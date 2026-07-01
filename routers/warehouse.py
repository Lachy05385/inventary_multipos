from typing import List
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
from routers.auth import get_current_user

router = APIRouter(prefix="/warehouse", tags=["warehouse"])

def get_warehouse_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

@router.post("/products", response_model=ProductSchema)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    # Verificar si SKU ya existe
    existing_product = db.query(Product).filter(Product.sku == product.sku).first()
    if existing_product:
        raise HTTPException(status_code=400, detail="SKU already exists")
    
    db_product = Product(
        name=product.name,
        description=product.description,
        sku=product.sku,
        price=product.price,
        cost=product.cost
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Crear registro de stock en almacén
    warehouse_stock = WarehouseStock(
        product_id=db_product.id,
        quantity=0
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

@router.put("/products/{product_id}", response_model=ProductSchema)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_warehouse_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Actualizar solo los campos proporcionados
    update_data = product_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
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
    query = db.query(WarehouseStock).options(joinedload(WarehouseStock.product))
    
    if low_stock_only:
        query = query.filter(WarehouseStock.quantity <= WarehouseStock.min_stock)
    
    stock = query.all()
    
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