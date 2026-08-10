from typing import List,Optional
from fastapi import UploadFile,File,Form
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.database import get_db
from models.user_models import User, UserRole
from models.inventory_models import Product, WarehouseStock, POSLocation, TransferToPOS, POSStock
from schemas.inventory_schemas import (
    ProductCreate, Product as ProductSchema, ProductUpdate,
    WarehouseStock as WarehouseStockSchema, WarehouseStockWithProduct,
    TransferCreate, Transfer as TransferSchema, TransferWithDetails,
    POSStockWithProduct
)
import aiofiles
from routers.auth import get_current_user

router = APIRouter(prefix="/warehouse", tags=["warehouse"])

def get_warehouse_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

@router.post("/products", response_model=ProductSchema)
async def create_product(
    # Datos del producto como form-data (para poder recibir archivo)
    name: str = Form(...),
    description: Optional[str] = Form(None),
    sku: str = Form(...),
    price: float = Form(...),
    cost: Optional[float] = Form(None),
    min_stock: int = Form(0),
    category_id: Optional[int] = Form(None),
    has_inventory: bool = Form(True),
    image: UploadFile = File(None),   # archivo opcional
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    # Verificar SKU
    existing = db.query(Product).filter(Product.sku == sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")

    # Guardar imagen si se envió
    image_url = None
    if image:
        # Validar extensión (opcional)
        allowed = ["image/png", "image/jpeg", "image/jpg"]
        if image.content_type not in allowed:
            raise HTTPException(status_code=400, detail="Invalid image format. Only PNG, JPG, JPEG allowed")
        
        # Definir ruta: static/img/{sku}.png (siempre png por simplicidad, pero podrías mantener extensión)
        # Forzamos .png para uniformar
        file_extension = ".png"
        filename = f"{sku}{file_extension}"
        file_path = f"static/img/{filename}"
        
        # Crear directorio si no existe
        os.makedirs("static/img", exist_ok=True)
        
        # Guardar archivo de forma asíncrona
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await image.read()
            await out_file.write(content)
        
        # Guardar URL relativa para servir estáticamente
        image_url = f"/static/img/{filename}"

    # Crear producto
    db_product = Product(
        name=name,
        description=description,
        sku=sku,
        price=price,
        cost=cost,
        min_stock=min_stock,
        category_id=category_id,
        has_inventory=has_inventory,
        image_url=image_url
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # Crear stock en almacén (siempre con cantidad 0)
    if has_inventory:
        warehouse_stock = WarehouseStock(
            product_id=db_product.id,
            quantity=0,
            min_stock=10
        )
        db.add(warehouse_stock)
        db.commit()

    return db_product


@router.get("/products", response_model=List[ProductSchema])
def read_products(
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None, description="Search by name or SKU"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    query = db.query(Product)
    
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) | 
            (Product.sku.ilike(f"%{search}%"))
        )
    
    products = query.offset(skip).limit(limit).all()
    return products

# Entradas de compras 
from models.inventory_models import Supplier, PurchaseEntry, PurchaseItem, WarehouseStock
from schemas.inventory_schemas import PurchaseEntryCreate, PurchaseEntryWithDetails
from models.inventory_models import WarehouseEntry
from datetime import datetime

@router.post("/purchase-entries", response_model=PurchaseEntryWithDetails)
def create_purchase_entry(
    entry_data: PurchaseEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    # 1. Verificar proveedor
    supplier = db.query(Supplier).filter(Supplier.id == entry_data.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # 2. Validar y calcular total
    total = 0
    items_data = []
    for item in entry_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        if not product.has_inventory:
            raise HTTPException(status_code=400, detail=f"Product {product.name} does not have inventory")
        
        subtotal = item.quantity * item.unit_price - (item.discount or 0)
        total += subtotal
        items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "subtotal": subtotal,
            "discount": item.discount or 0
        })
    
    # 3. Crear entrada
    db_entry = PurchaseEntry(
        supplier_id=entry_data.supplier_id,
        total_amount=total,
        paid_amount=entry_data.paid_amount if entry_data.paid_amount else 0,
        status="pending" if (entry_data.paid_amount or 0) < total else "paid",
        notes=entry_data.notes,
        document_number=entry_data.document_number,
        document_date=entry_data.document_date or datetime.now()
    )
    db.add(db_entry)
    db.flush()  # para obtener el id
    
    # 4. Crear items y actualizar stock
    for data in items_data:
        item = PurchaseItem(
            purchase_entry_id=db_entry.id,
            **data
        )
        db.add(item)
        
        # Actualizar stock en warehouse
        warehouse = db.query(WarehouseStock).filter(
            WarehouseStock.product_id == data["product_id"]
        ).first()
        if warehouse:
            warehouse.quantity += data["quantity"]
        else:
            # Si no existe, crear (solo si el producto tiene inventario)
            product = db.query(Product).filter(Product.id == data["product_id"]).first()
            if product and product.has_inventory:
                new_stock = WarehouseStock(
                    product_id=data["product_id"],
                    quantity=data["quantity"],
                    min_stock=product.min_stock or 10
                )
                db.add(new_stock)
    
    db.commit()
    db.refresh(db_entry)
    
    # 5. Cargar relaciones para la respuesta
    result = db.query(PurchaseEntry).options(
        joinedload(PurchaseEntry.supplier),
        joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
    ).filter(PurchaseEntry.id == db_entry.id).first()


    # 6. Agregar balance manualmente si no está en el esquema
    result = db.query(PurchaseEntry).options(
            joinedload(PurchaseEntry.supplier),
            joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
        ).filter(PurchaseEntry.id == db_entry.id).first()

    # ✅ Ya NO asignamos balance, el esquema lo calcula solo
    return result  # FastAPI usará el response_model para validar y serializar

@router.post("/entries/{entry_id}/cancel", response_model=dict)
def cancel_warehouse_entry(
    entry_id: int,
    reason: str = Query(..., description="Motivo de la cancelación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    """
    Cancela una entrada de inventario en el warehouse.
    - Revertir el stock del producto.
    - Marcar la entrada como cancelada.
    - Registrar el motivo y el usuario que cancela.
    """
    # Buscar la entrada en el warehouse
    entry = db.query(WarehouseEntry).filter(WarehouseEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    
    # Verificar que no esté ya cancelada
    if entry.status == "cancelled":
        raise HTTPException(status_code=400, detail="Esta entrada ya está cancelada")
    
    # Verificar que el producto tenga suficiente stock para descontar
    stock = db.query(WarehouseStock).filter(WarehouseStock.product_id == entry.product_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Producto no encontrado en el almacén")
    
    if stock.quantity < entry.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cancelar: stock insuficiente (stock actual: {stock.quantity}, entrada: {entry.quantity})"
        )
    
    # Revertir el stock
    stock.quantity -= entry.quantity
    stock.last_updated = datetime.now()
    
    # Marcar la entrada como cancelada
    entry.status = "cancelled"
    entry.cancelled_by = current_user.id
    entry.cancelled_at = datetime.now()
    entry.cancellation_reason = reason
    
    db.commit()
    
    return {
        "message": "Entrada cancelada exitosamente",
        "entry_id": entry_id,
        "product_id": entry.product_id,
        "quantity_reverted": entry.quantity,
        "new_stock": stock.quantity,
        "cancelled_by": current_user.username
    }

#OBTENER ENTRADAS POR PEDIODO 

# routers/suppliers.py
from datetime import date
from typing import Optional
from fastapi import Query
from typing import Optional, List, TYPE_CHECKING  # ⬅️ Agregar TYPE_CHECKING
from schemas.enums import DocumentType, PurchaseEntryStatus

@router.get("/entries", response_model=List[PurchaseEntryWithDetails])
def list_purchase_entries(
    start_date: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    supplier_id: Optional[int] = Query(None, description="ID del proveedor"),
    status: Optional[PurchaseEntryStatus] = Query(None, description="Estado de la entrada"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    """
    Lista las entradas de compra con filtros opcionales por:
    - Rango de fechas (start_date y end_date)
    - Proveedor (supplier_id)
    - Estado (status)
    """
    query = db.query(PurchaseEntry).options(
        joinedload(PurchaseEntry.supplier),
        joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
    )

    if start_date:
        query = query.filter(PurchaseEntry.entry_date >= start_date)
    if end_date:
        # Para incluir todo el día, sumamos 1 día y restamos 1 segundo
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(PurchaseEntry.entry_date <= end_datetime)
    if supplier_id:
        query = query.filter(PurchaseEntry.supplier_id == supplier_id)
    if status:
        query = query.filter(PurchaseEntry.status == status)

    entries = query.order_by(PurchaseEntry.entry_date.desc()).offset(skip).limit(limit).all()
    return entries

@router.get("/products/{product_id}", response_model=ProductSchema)
def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
import os

@router.put("/products/{product_id}", response_model=ProductSchema)
async def update_product(
    product_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    cost: Optional[float] = Form(None),
    min_stock: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    has_inventory: Optional[bool] = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Si se envía SKU, verificar que no exista otro producto con ese SKU
    if sku and sku != product.sku:
        existing = db.query(Product).filter(Product.sku == sku).first()
        if existing:
            raise HTTPException(status_code=400, detail="SKU already exists")
    
    # Actualizar campos (solo los proporcionados)
    update_data = {}
    if name is not None: update_data["name"] = name
    if description is not None: update_data["description"] = description
    if sku is not None: update_data["sku"] = sku
    if price is not None: update_data["price"] = price
    if cost is not None: update_data["cost"] = cost
    if min_stock is not None: update_data["min_stock"] = min_stock
    if category_id is not None: update_data["category_id"] = category_id

    for field, value in update_data.items():
        setattr(product, field, value)

    # Manejar imagen
    if image:
        # Validar formato
        allowed = ["image/png", "image/jpeg", "image/jpg"]
        if image.content_type not in allowed:
            raise HTTPException(status_code=400, detail="Invalid image format. Only PNG, JPG, JPEG allowed")
        
        # Determinar nombre de archivo: usar SKU actual o el nuevo si se cambió
        current_sku = sku if sku else product.sku
        file_extension = ".png"
        filename = f"{current_sku}{file_extension}"
        file_path = f"static/img/{filename}"
        
        # Eliminar imagen anterior si existe y no tiene el mismo nombre
        if product.image_url:
            old_filename = product.image_url.split("/")[-1]
            old_path = f"static/img/{old_filename}"
            if os.path.exists(old_path) and old_filename != filename:
                os.remove(old_path)  # eliminar archivo viejo

        os.makedirs("static/img", exist_ok=True)
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await image.read()
            await out_file.write(content)
        
        product.image_url = f"/static/img/{filename}"

    # Si se cambia a has_inventory=True pero no tiene warehouse_stock, crearlo
    if has_inventory is True and not product.warehouse_stock:
        new_stock = WarehouseStock(product_id=product.id, quantity=0, min_stock=10)
        db.add(new_stock)

    db.commit()
    db.refresh(product)
    return product
    
from sqlalchemy.orm import joinedload

@router.get("/stock", response_model=List[WarehouseStockWithProduct])
def read_warehouse_stock(
    low_stock_only: bool = Query(False, description="Show only low stock items"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    # Carga eager de la relación 'product' para evitar consultas N+1
    query = db.query(WarehouseStock).join(Product).filter(Product.has_inventory == True)
    
    if low_stock_only:
        query = query.filter(WarehouseStock.quantity <= WarehouseStock.min_stock)
    
    stock = query.options(joinedload(WarehouseStock.product)).all()
    
    # Construye la respuesta usando el esquema Pydantic
    result = []
    for item in stock:
        result.append(WarehouseStockWithProduct(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            min_stock=item.min_stock,
            last_updated=item.last_updated,
            product=item.product   # ✅ ahora 'product' existe
        ))
    
    return result

#  NUEVO 
router.get("/low-stock", response_model=List[WarehouseStockWithProduct])
def get_low_stock(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    stock = db.query(WarehouseStock).join(Product).filter(
        Product.has_inventory == True,
        WarehouseStock.quantity < WarehouseStock.min_stock
    ).options(joinedload(WarehouseStock.product)).all()
    return stock

#  NUEVO 

@router.put("/stock/{product_id}", response_model=WarehouseStockSchema)
def update_warehouse_stock(
    product_id: int,
    quantity: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    warehouse_stock = db.query(WarehouseStock).filter(
        WarehouseStock.product_id == product_id
    ).first()
    
    if not warehouse_stock:
        raise HTTPException(status_code=404, detail="Product stock not found")
    
    warehouse_stock.quantity = quantity
    db.commit()
    db.refresh(warehouse_stock)
    
    return warehouse_stock

@router.post("/transfer", response_model=TransferWithDetails)
def transfer_to_pos(
    transfer: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    
    # Verificar que el producto existe y tiene inventario
    product = db.query(Product).filter(Product.id == transfer.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.has_inventory:
        raise HTTPException(status_code=400, detail="Product does not require inventory (is a service)")
    
        
    # Verificar stock en almacén
    warehouse_stock = db.query(WarehouseStock).filter(
        WarehouseStock.product_id == transfer.product_id
    ).first()
    
    
    if not warehouse_stock:
        raise HTTPException(status_code=404, detail="Product not found in warehouse")
    
    if warehouse_stock.quantity < transfer.quantity:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient stock in warehouse. Available: {warehouse_stock.quantity}"
        )
    
    # Verificar punto de venta
    pos_location = db.query(POSLocation).filter(
        POSLocation.id == transfer.pos_location_id
    ).first()
    
    if not pos_location:
        raise HTTPException(status_code=404, detail="POS location not found")
    
    # Crear transferencia
    db_transfer = TransferToPOS(
        warehouse_stock_id=warehouse_stock.id,
        pos_location_id=transfer.pos_location_id,
        product_id=transfer.product_id,
        quantity=transfer.quantity,
        transferred_by=current_user.id
    )
    
    # Actualizar stocks
    warehouse_stock.quantity -= transfer.quantity
    
    # Actualizar o crear stock en POS
    pos_stock = db.query(POSStock).filter(
        POSStock.product_id == transfer.product_id,
        POSStock.pos_location_id == transfer.pos_location_id
    ).first()
    
    if pos_stock:
        pos_stock.quantity += transfer.quantity
    else:
        pos_stock = POSStock(
            product_id=transfer.product_id,
            pos_location_id=transfer.pos_location_id,
            quantity=transfer.quantity
        )
        db.add(pos_stock)
    
    db.add(db_transfer)
    db.commit()
    db.refresh(db_transfer)
    
    # Obtener detalles completos para la respuesta
    transfer_with_details = TransferWithDetails(
        id=db_transfer.id,
        product_id=db_transfer.product_id,
        pos_location_id=db_transfer.pos_location_id,
        quantity=db_transfer.quantity,
        warehouse_stock_id=db_transfer.warehouse_stock_id,
        transferred_by=db_transfer.transferred_by,
        transfer_date=db_transfer.transfer_date,
        status=db_transfer.status,
        product=db_transfer.product,
        pos_location=db_transfer.pos_location
    )
    
    return transfer_with_details

@router.get("/transfers", response_model=List[TransferWithDetails])
def read_transfers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    transfers = db.query(TransferToPOS).offset(skip).limit(limit).all()
    
    result = []
    for transfer in transfers:
        result.append(TransferWithDetails(
            id=transfer.id,
            product_id=transfer.product_id,
            pos_location_id=transfer.pos_location_id,
            quantity=transfer.quantity,
            warehouse_stock_id=transfer.warehouse_stock_id,
            transferred_by=transfer.transferred_by,
            transfer_date=transfer.transfer_date,
            status=transfer.status,
            product=transfer.product,
            pos_location=transfer.pos_location
        ))
    
    return result


# routers/warehouse.py
import csv
import io
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from models.inventory_models import Category
from datetime import datetime

# ========== EXPORTAR PRODUCTOS A CSV ==========
@router.get("/products/export/csv")
def export_products_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    """
    Exporta todos los productos a un archivo CSV.
    Incluye: id, name, description, sku, price, cost, image_url, 
             min_stock, category_name, has_inventory, created_at
    """
    products = db.query(Product).options(joinedload(Product.category)).all()
    
    # Crear buffer en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Escribir cabeceras
    writer.writerow([
        "id", "name", "description", "sku", "price", "cost", 
        "image_url", "min_stock", "category_name", "has_inventory", "created_at"
    ])
    
    # Escribir datos
    for p in products:
        writer.writerow([
            p.id,
            p.name,
            p.description or "",
            p.sku,
            p.price,
            p.cost or 0,
            p.image_url or "",
            p.min_stock,
            p.category.name if p.category else "",
            str(p.has_inventory),
            p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else ""
        ])
    
    # Preparar respuesta como archivo descargable
    output.seek(0)
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=productos_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )
    return response

# ========== IMPORTAR PRODUCTOS DESDE CSV ==========
@router.post("/products/import/csv")
def import_products_csv(
    file: UploadFile = File(...),
    update_existing: bool = True,  # Si True, actualiza; si False, omite duplicados
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    """
    Importa productos desde un archivo CSV.
    
    - Si SKU existe y update_existing=True: actualiza el producto.
    - Si SKU existe y update_existing=False: omite el producto.
    - Si SKU no existe: crea un nuevo producto.
    - La categoría se busca por nombre; si no existe, se crea automáticamente.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "El archivo debe ser CSV")
    
    # Leer contenido del archivo
    contents = file.file.read().decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(contents))
    
    stats = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": []
    }
    
    for row_num, row in enumerate(csv_reader, start=2):  # start=2 porque fila 1 es cabecera
        try:
            # Validar campos obligatorios
            sku = row.get("sku", "").strip()
            name = row.get("name", "").strip()
            price_str = row.get("price", "").strip()
            
            if not sku or not name or not price_str:
                stats["errors"].append(f"Fila {row_num}: SKU, nombre y precio son obligatorios")
                continue
            
            # Buscar categoría por nombre
            category_name = row.get("category_name", "").strip()
            category_id = None
            if category_name:
                category = db.query(Category).filter(Category.name == category_name).first()
                if not category:
                    # Crear categoría si no existe
                    category = Category(name=category_name)
                    db.add(category)
                    db.flush()
                category_id = category.id
            
            # Buscar producto existente
            existing = db.query(Product).filter(Product.sku == sku).first()
            
            if existing:
                if update_existing:
                    # Actualizar producto existente
                    existing.name = name
                    existing.description = row.get("description", "").strip() or None
                    existing.price = float(price_str)
                    cost_str = row.get("cost", "").strip()
                    existing.cost = float(cost_str) if cost_str else None
                    existing.image_url = row.get("image_url", "").strip() or None
                    min_stock_str = row.get("min_stock", "").strip()
                    existing.min_stock = int(min_stock_str) if min_stock_str else 0
                    existing.category_id = category_id
                    has_inventory_str = row.get("has_inventory", "True").strip().lower()
                    existing.has_inventory = has_inventory_str in ["true", "1", "yes"]
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                # Crear nuevo producto
                new_product = Product(
                    name=name,
                    description=row.get("description", "").strip() or None,
                    sku=sku,
                    price=float(price_str),
                    cost=float(row.get("cost", 0)) if row.get("cost", "").strip() else None,
                    image_url=row.get("image_url", "").strip() or None,
                    min_stock=int(row.get("min_stock", 0)) if row.get("min_stock", "").strip() else 0,
                    category_id=category_id,
                    has_inventory=row.get("has_inventory", "True").strip().lower() in ["true", "1", "yes"]
                )
                db.add(new_product)
                stats["created"] += 1
                
                # Crear stock en warehouse automáticamente
                warehouse_stock = WarehouseStock(
                    product_id=new_product.id,
                    quantity=0,
                    min_stock=10
                )
                db.add(warehouse_stock)
        
        except ValueError as e:
            stats["errors"].append(f"Fila {row_num}: Error en datos numéricos - {str(e)}")
        except Exception as e:
            stats["errors"].append(f"Fila {row_num}: {str(e)}")
    
    # Commit de todos los cambios
    db.commit()
    
    return {
        "message": "Importación completada",
        "stats": stats,
        "total_rows": len(list(csv_reader))  # Nota: esto no funcionará porque el reader ya se consumió
    }
    
    
# routers/warehouse.py
import csv
import io
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from models.inventory_models import Category
from datetime import datetime

# ========== EXPORTAR PRODUCTOS A CSV ==========
@router.get("/products/export/csv")
def export_products_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    """
    Exporta todos los productos a un archivo CSV.
    Incluye: id, name, description, sku, price, cost, image_url, 
             min_stock, category_name, has_inventory, created_at
    """
    products = db.query(Product).options(joinedload(Product.category)).all()
    
    # Crear buffer en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Escribir cabeceras
    writer.writerow([
        "id", "name", "description", "sku", "price", "cost", 
        "image_url", "min_stock", "category_name", "has_inventory", "created_at"
    ])
    
    # Escribir datos
    for p in products:
        writer.writerow([
            p.id,
            p.name,
            p.description or "",
            p.sku,
            p.price,
            p.cost or 0,
            p.image_url or "",
            p.min_stock,
            p.category.name if p.category else "",
            str(p.has_inventory),
            p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else ""
        ])
    
    # Preparar respuesta como archivo descargable
    output.seek(0)
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=productos_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )
    return response

# ========== IMPORTAR PRODUCTOS DESDE CSV ==========
@router.post("/products/import/csv")
def import_products_csv(
    file: UploadFile = File(...),
    update_existing: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "El archivo debe ser CSV")
    
    contents = file.file.read().decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(contents))
    
    stats = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": []
    }
    
    for row_num, row in enumerate(csv_reader, start=2):
        try:
            sku = row.get("sku", "").strip()
            name = row.get("name", "").strip()
            price_str = row.get("price", "").strip()
            
            if not sku or not name or not price_str:
                stats["errors"].append(f"Fila {row_num}: SKU, nombre y precio son obligatorios")
                continue
            
            # Buscar categoría
            category_name = row.get("category_name", "").strip()
            category_id = None
            if category_name:
                category = db.query(Category).filter(Category.name == category_name).first()
                if not category:
                    category = Category(name=category_name)
                    db.add(category)
                    db.flush()
                category_id = category.id
            
            # Buscar producto existente
            existing = db.query(Product).filter(Product.sku == sku).first()
            
            if existing:
                if update_existing:
                    existing.name = name
                    existing.description = row.get("description", "").strip() or None
                    existing.price = float(price_str)
                    cost_str = row.get("cost", "").strip()
                    existing.cost = float(cost_str) if cost_str else None
                    existing.image_url = row.get("image_url", "").strip() or None
                    min_stock_str = row.get("min_stock", "").strip()
                    existing.min_stock = int(min_stock_str) if min_stock_str else 0
                    existing.category_id = category_id
                    has_inventory_str = row.get("has_inventory", "True").strip().lower()
                    existing.has_inventory = has_inventory_str in ["true", "1", "yes"]
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                # Crear nuevo producto
                new_product = Product(
                    name=name,
                    description=row.get("description", "").strip() or None,
                    sku=sku,
                    price=float(price_str),
                    cost=float(row.get("cost", 0)) if row.get("cost", "").strip() else None,
                    image_url=row.get("image_url", "").strip() or None,
                    min_stock=int(row.get("min_stock", 0)) if row.get("min_stock", "").strip() else 0,
                    category_id=category_id,
                    has_inventory=row.get("has_inventory", "True").strip().lower() in ["true", "1", "yes"]
                )
                db.add(new_product)
                db.flush()  # ⬅️ OBTENER ID
                stats["created"] += 1
                
                # Crear stock en warehouse SOLO si tiene inventario
                if new_product.has_inventory:
                    warehouse_stock = WarehouseStock(
                        product_id=new_product.id,
                        quantity=0,
                        min_stock=10
                    )
                    db.add(warehouse_stock)
        
        except ValueError as e:
            stats["errors"].append(f"Fila {row_num}: Error en datos numéricos - {str(e)}")
        except Exception as e:
            stats["errors"].append(f"Fila {row_num}: {str(e)}")
    
    db.commit()
    
    return {
        "message": "Importación completada",
        "stats": stats,
        "total_rows": row_num - 1  # Aproximado, ya que el reader se consumió
    }