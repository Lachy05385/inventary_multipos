from typing import List,Optional
from fastapi import UploadFile,File,Form
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session,joinedload
from database.database import get_db
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from models.user_models import User, UserRole
from models.inventory_models import Product, WarehouseStock, POSLocation, TransferToPOS, POSStock
from schemas.inventory_schemas import (
    ProductCreate, Product as ProductSchema, ProductUpdate,
    WarehouseStock as WarehouseStockSchema, WarehouseStockWithProduct, TransferReceive,
    TransferCreate, Transfer as TransferSchema, TransferWithDetails,Transfer, TransferResponse,
    POSStockWithProduct, 
)

from models.inventory_models import Transfer, TransferItem, TransferStatus

import aiofiles
from routers.auth import get_current_user

router = APIRouter(prefix="/warehouse", tags=["warehouse"])






def get_warehouse_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

def _cargar_transfer_completa(db: Session, transfer_id: int):
    """
    Carga una transferencia con todas sus relaciones:
    items, productos, POS destino, usuario que envió y usuario que recibió.
    """
    return (
        db.query(Transfer)
        .options(
            joinedload(Transfer.items).joinedload(TransferItem.product),
            joinedload(Transfer.pos_location),
            joinedload(Transfer.sent_by),
            joinedload(Transfer.received_by),
        )
        .filter(Transfer.id == transfer_id)
        .first()
    )



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

#querys 
'''def get_tenant_id(current_user: User) -> int:
    """Hoy siempre 1. Mañana: current_user.tenant_id"""
    return 1  # o current_user.tenant_id si ya lo tenés

@router.get("/products")
def read_products(..., tenant_id: int = Depends(get_tenant_id)):
    return db.query(Product).filter(Product.tenant_id == tenant_id).all()

'''
def _to_transfer_response(transfer: Transfer) -> dict:
    return {
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "pos_location_id": transfer.pos_location_id,
        "pos_location": transfer.pos_location,
        "sent_by_id": transfer.sent_by_id,
        "sent_by_name": transfer.sent_by.full_name if transfer.sent_by else None,
        "sent_at": transfer.sent_at,
        "received_by_id": transfer.received_by_id,
        "received_by_name": transfer.received_by.full_name if transfer.received_by else None,
        "received_at": transfer.received_at,
        "cancelled_by_id": transfer.cancelled_by_id,
        "cancelled_by_name": transfer.cancelled_by.full_name if transfer.cancelled_by else None,
        "cancelled_at": transfer.cancelled_at,
        "cancelled_reason": transfer.cancelled_reason,
        "status": transfer.status,
        "notes": transfer.notes,
        "total_items": transfer.total_items,
        "total_units": transfer.total_units,
        "items": transfer.items,
    }


@router.get("/transfers/pending", response_model=List[TransferResponse])
def read_pending_transfers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve las transferencias pendientes para el POS del cajero autenticado.
    Solo accesible para CASHIER (para su propio POS) o ADMIN/WAREHOUSE.
    """
    if current_user.role == UserRole.CASHIER:
        if not current_user.pos_location_id:
            return []
        transfers = (
            db.query(Transfer)
            .options(
                joinedload(Transfer.items).joinedload(TransferItem.product),
                joinedload(Transfer.pos_location),
                joinedload(Transfer.sent_by),
            )
            .filter(
                Transfer.pos_location_id == current_user.pos_location_id,
                Transfer.status == TransferStatus.PENDING.value,
            )
            .order_by(Transfer.sent_at.asc())
            .all()
        )
    else:
        # Admin/warehouse ven todas las pendientes (opcional)
        transfers = (
            db.query(Transfer)
            .options(
                joinedload(Transfer.items).joinedload(TransferItem.product),
                joinedload(Transfer.pos_location),
                joinedload(Transfer.sent_by),
            )
            .filter(Transfer.status == TransferStatus.PENDING.value)
            .order_by(Transfer.sent_at.asc())
            .all()
        )

    return [_to_transfer_response(t) for t in transfers]






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

# routers/warehouse.py
# routers/warehouse.py
@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Verificar si tiene stock o transferencias
    if product.warehouse_stock and product.warehouse_stock.quantity > 0:
        raise HTTPException(status_code=400, detail="No se puede eliminar un producto con stock")

    # Eliminar imagen si existe
    if product.image_url:
        import os
        old_path = product.image_url.lstrip('/')
        if os.path.exists(old_path):
            os.remove(old_path)

    db.delete(product)
    db.commit()
    return {"message": f"Producto {product.name} eliminado"}


# Entradas de compras 
from models.inventory_models import Supplier, PurchaseEntry, PurchaseItem, WarehouseStock
from schemas.inventory_schemas import PurchaseEntryCreate, PurchaseEntryWithDetails
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

#get purchase enters 
@router.get("/purchase-entries", response_model=List[PurchaseEntryWithDetails])
def read_purchase_entries(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros a devolver"),
    status_filter: Optional[str] = Query(None, description="Filtrar por estado: pending, partial, paid"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    # 1. Construir query base
    query = db.query(PurchaseEntry)

    # 2. Filtro opcional por estado
    if status_filter:
        query = query.filter(PurchaseEntry.status == status_filter)

    # 3. Eager loading (evita el problema N+1)
    query = query.options(
        joinedload(PurchaseEntry.supplier),
        joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
    )

    # 4. Ordenar: más reciente primero
    query = query.order_by(PurchaseEntry.entry_date.desc())

    # 5. Aplicar paginación y ejecutar
    entries = query.offset(skip).limit(limit).all()

    return entries
# Un proveedor 
@router.get("/purchase-entries/supplier/{supplier_id}", response_model=List[PurchaseEntryWithDetails])
def read_purchase_entries_by_supplier(
    supplier_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
    ):
    # 1. Verificar que el proveedor existe (mejor UX: 404 claro en vez de lista vacía)
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id)

    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    # 2. Query con filtro por supplier_id
    entries = (
        db.query(PurchaseEntry).filter(PurchaseEntry.supplier_id == supplier_id).options(
            joinedload(PurchaseEntry.supplier),
            joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
            )
        .order_by(PurchaseEntry.entry_date.desc())
        .offset(skip).limit(limit)
        .all()
        )
    
    return entries

from datetime import timedelta,date

# obtener entrdas entre dos fechas
@router.get("/purchase-entries/period", response_model=List[PurchaseEntryWithDetails])
def read_purchase_entries_by_period(
    start_date: date = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
     # 1. Validar que el rango sea lógico
    if start_date > end_date:
        raise HTTPException(
        status_code=400,
        detail="start_date no puede ser mayor que end_date"
        )
    # 2. Convertir fechas a datetime con horas extremas
    # start_date 00:00:00 → end_date 23:59:59.999999
    start_dt = datetime.combine(start_date, time.min) # 00:00:00
    end_dt = datetime.combine(end_date, time.max) # 23:59:59.999999

    # 3. Query
    entries = (
        db.query(PurchaseEntry)
        .filter(
        PurchaseEntry.entry_date >= start_dt,
        PurchaseEntry.entry_date <= end_dt
    )
    .options(
    joinedload(PurchaseEntry.supplier),
    joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
    )
    .order_by(PurchaseEntry.entry_date.desc()).offset(skip).limit(limit).all()
    )
    
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
@router.get("/stock/consolidated")
def get_consolidated_stock(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stock consolidado de todos los productos en:
    - Almacén central
    - Cada punto de venta activo
    - Total global
    Solo accesible para ADMIN.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver el stock consolidado")

    # 1. Todos los POS activos (para las columnas)
    pos_locations = db.query(POSLocation).filter(POSLocation.is_active == True).order_by(POSLocation.name).all()
    pos_ids = [p.id for p in pos_locations]

    # 2. Todos los productos que manejan inventario
    productos = (
        db.query(Product)
        .filter(Product.has_inventory == True)
        .order_by(Product.name)
        .all()
    )

    # 3. Stock del almacén (mapa product_id -> quantity)
    warehouse_stock_rows = db.query(WarehouseStock).all()
    warehouse_map = {ws.product_id: ws.quantity for ws in warehouse_stock_rows}

    # 4. Stock de todos los POS (mapa compuesto (pos_id, product_id) -> quantity)
    pos_stock_rows = (
        db.query(POSStock)
        .filter(POSStock.pos_location_id.in_(pos_ids) if pos_ids else False)
        .all()
    )
    pos_stock_map = {}
    for ps in pos_stock_rows:
        pos_stock_map[(ps.pos_location_id, ps.product_id)] = ps.quantity

    # 5. Armar respuesta
    resultado = []
    for prod in productos:
        wh_qty = warehouse_map.get(prod.id, 0)

        pos_breakdown = []
        total_pos = 0
        for pos in pos_locations:
            qty = pos_stock_map.get((pos.id, prod.id), 0)
            pos_breakdown.append({
                "pos_id": pos.id,
                "pos_name": pos.name,
                "quantity": qty,
            })
            total_pos += qty

        total_global = wh_qty + total_pos

        # Estado del producto
        if total_global == 0:
            estado = "sin_stock"
        elif wh_qty <= prod.min_stock:
            estado = "bajo_almacen"
        elif any(pb["quantity"] == 0 for pb in pos_breakdown) and pos_breakdown:
            estado = "faltante_en_pos"
        else:
            estado = "ok"

        resultado.append({
            "product_id": prod.id,
            "sku": prod.sku,
            "name": prod.name,
            "category": prod.category.name if prod.category else None,
            "min_stock": prod.min_stock or 0,
            "price": prod.price,
            "has_inventory": prod.has_inventory,
            "warehouse_quantity": wh_qty,
            "pos_breakdown": pos_breakdown,
            "total_in_pos": total_pos,
            "total_global": total_global,
            "status": estado,
        })

    # 6. Resumen general
    total_products = len(resultado)
    sin_stock_global = sum(1 for r in resultado if r["status"] == "sin_stock")
    bajo_almacen = sum(1 for r in resultado if r["status"] == "bajo_almacen")
    faltantes_en_pos = sum(1 for r in resultado if r["status"] == "faltante_en_pos")

    return {
        "pos_locations": [{"id": p.id, "name": p.name} for p in pos_locations],
        "total_products": total_products,
        "summary": {
            "sin_stock_global": sin_stock_global,
            "bajo_almacen": bajo_almacen,
            "faltantes_en_pos": faltantes_en_pos,
        },
        "products": resultado,
    }








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




# ==================== STOCK CONSOLIDADO ====================
@router.post("/transfers/{transfer_id}/cancel", response_model=TransferResponse)
def cancel_transfer(
    transfer_id: int,
    reason: Optional[str] = Query(None, description="Motivo de la cancelación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transfer = _cargar_transfer_completa(db, transfer_id)
    if not transfer:
        raise HTTPException(404, "Transferencia no encontrada")
    if transfer.status != TransferStatus.PENDING.value:
        raise HTTPException(400, f"No se puede cancelar una transferencia en estado '{transfer.status}'")

    # Permisos: quien la envió (warehouse) o admin
    if current_user.role == UserRole.ADMIN:
        pass  # admin siempre puede
    elif current_user.id == transfer.sent_by_id:
        pass  # el que la envió puede cancelarla
    elif current_user.role == UserRole.CASHIER and current_user.pos_location_id == transfer.pos_location_id:
        pass  # el cashier del POS destino también puede rechazarla
    else:
        raise HTTPException(403, "Sin permisos para cancelar esta transferencia")

    # Devolver stock al almacén
    for item in transfer.items:
        ws = db.query(WarehouseStock).filter(
            WarehouseStock.product_id == item.product_id
        ).first()
        if ws:
            ws.quantity += item.quantity
        else:
            # Si no existe, crear (raro, pero por seguridad)
            db.add(WarehouseStock(product_id=item.product_id, quantity=item.quantity))

    transfer.status = TransferStatus.CANCELLED.value
    transfer.cancelled_by_id = current_user.id
    transfer.cancelled_at = datetime.utcnow()
    transfer.cancelled_reason = reason or "Cancelada por el usuario"

    db.commit()
    db.refresh(transfer)
    return _to_transfer_response(_cargar_transfer_completa(db, transfer.id))
