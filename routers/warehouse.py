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