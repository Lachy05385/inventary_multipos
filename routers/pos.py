from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.database import get_db
from models.user_models import User, UserRole
from models.inventory_models import POSLocation, POSStock, Product
from models.cash_models import Sale, SaleItem, CashRegister
from schemas.inventory_schemas import POSLocationCreate, POSLocation as POSLocationSchema, POSStockWithProduct
from schemas.cash_schemas import SaleCreate, Sale as SaleSchema, SaleWithDetails, SaleItemCreate
from routers.auth import get_current_user

router = APIRouter(prefix="/pos", tags=["point-of-sale"])

@router.post("/locations", response_model=POSLocationSchema)
def create_pos_location(
    location: POSLocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_location = POSLocation(
        name=location.name,
        address=location.address
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    
    # Crear caja registradora para este punto de venta
    cash_register = CashRegister(pos_location_id=db_location.id)
    db.add(cash_register)
    db.commit()
    
    return db_location

@router.get("/locations", response_model=List[POSLocationSchema])
def read_pos_locations(
    active_only: bool = Query(True, description="Show only active locations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(POSLocation)
    
    if active_only:
        query = query.filter(POSLocation.is_active == True)
    
    locations = query.all()
    return locations

@router.get("/{pos_id}/stock", response_model=List[POSStockWithProduct])
def read_pos_stock(
    pos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar que el usuario tenga acceso a este POS
    if current_user.role == UserRole.CASHIER and current_user.pos_location_id != pos_id:
        raise HTTPException(status_code=403, detail="Access denied to this POS location")
    
    # Verificar que el POS existe
    pos_location = db.query(POSLocation).filter(POSLocation.id == pos_id).first()
    if not pos_location:
        raise HTTPException(status_code=404, detail="POS location not found")
    
    stock_items = db.query(POSStock).filter(POSStock.pos_location_id == pos_id).all()
    
    result = []
    for item in stock_items:
        result.append(POSStockWithProduct(
            id=item.id,
            product_id=item.product_id,
            pos_location_id=item.pos_location_id,
            quantity=item.quantity,
            last_updated=item.last_updated,
            product=stock.product,         # ⭐ ahora existe
            pos_location=stock.pos_location  # ⭐ ahora existe
            
        ))
    
    return result

@router.post("/{pos_id}/sale", response_model=SaleWithDetails)
def create_sale(
    pos_id: int,
    sale: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar que el cajero tenga acceso a este POS
    if current_user.role == UserRole.CASHIER and current_user.pos_location_id != pos_id:
        raise HTTPException(status_code=403, detail="Access denied to this POS location")
    
    # Verificar que el POS existe
    pos_location = db.query(POSLocation).filter(POSLocation.id == pos_id).first()
    if not pos_location:
        raise HTTPException(status_code=404, detail="POS location not found")
    
    # Verificar stock y calcular total
    total_amount = 0
    sale_items_data = []
    
    for item in sale.items:
        # Verificar stock en POS
        pos_stock = db.query(POSStock).filter(
            POSStock.pos_location_id == pos_id,
            POSStock.product_id == item.product_id
        ).first()
        
        if not pos_stock:
            raise HTTPException(
                status_code=400, 
                detail=f"Product {item.product_id} not available at this POS"
            )
        
        if pos_stock.quantity < item.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock for product {item.product_id}. Available: {pos_stock.quantity}"
            )
        
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        subtotal = product.price * item.quantity
        total_amount += subtotal
        
        sale_items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": product.price,
            "subtotal": subtotal,
            "product_name": product.name
        })
    
    # Verificar efectivo recibido
    if sale.cash_received < total_amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient cash received. Total: {total_amount}, Received: {sale.cash_received}"
        )
    
    change = sale.cash_received - total_amount
    
    # Crear venta
    db_sale = Sale(
        pos_location_id=pos_id,
        cashier_id=current_user.id,
        total_amount=total_amount,
        cash_received=sale.cash_received,
        change=change
    )
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)
    
    # Crear items de venta y actualizar stock
    sale_items_with_details = []
    for item_data in sale_items_data:
        sale_item = SaleItem(
            sale_id=db_sale.id,
            product_id=item_data["product_id"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            subtotal=item_data["subtotal"]
        )
        db.add(sale_item)
        
        # Actualizar stock en POS
        pos_stock = db.query(POSStock).filter(
            POSStock.pos_location_id == pos_id,
            POSStock.product_id == item_data["product_id"]
        ).first()
        pos_stock.quantity -= item_data["quantity"]
        
        # Preparar detalles para la respuesta
        sale_items_with_details.append({
            "id": sale_item.id,
            "sale_id": sale_item.sale_id,
            "product_id": sale_item.product_id,
            "quantity": sale_item.quantity,
            "unit_price": sale_item.unit_price,
            "subtotal": sale_item.subtotal,
            "product_name": item_data["product_name"]
        })
    
    # Actualizar caja registradora
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == pos_id
    ).first()
    cash_register.current_balance += total_amount
    
    db.commit()
    db.refresh(db_sale)
    
    # Construir respuesta con detalles
    sale_with_details = SaleWithDetails(
        id=db_sale.id,
        pos_location_id=db_sale.pos_location_id,
        cashier_id=db_sale.cashier_id,
        total_amount=db_sale.total_amount,
        cash_received=db_sale.cash_received,
        change=db_sale.change,
        sale_date=db_sale.sale_date,
        sale_items=sale_items_with_details,
        cashier_name=current_user.full_name,
        pos_location_name=pos_location.name
    )
    
    return sale_with_details

@router.get("/{pos_id}/sales", response_model=List[SaleWithDetails])
def read_pos_sales(
    pos_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar permisos
    if current_user.role == UserRole.CASHIER and current_user.pos_location_id != pos_id:
        raise HTTPException(status_code=403, detail="Access denied to this POS location")
    
    sales = db.query(Sale).filter(Sale.pos_location_id == pos_id).offset(skip).limit(limit).all()
    
    result = []
    for sale in sales:
        sale_items_with_details = []
        for item in sale.sale_items:
            sale_items_with_details.append({
                "id": item.id,
                "sale_id": item.sale_id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
                "product_name": item.product.name
            })
        
        result.append(SaleWithDetails(
            id=sale.id,
            pos_location_id=sale.pos_location_id,
            cashier_id=sale.cashier_id,
            total_amount=sale.total_amount,
            cash_received=sale.cash_received,
            change=sale.change,
            sale_date=sale.sale_date,
            sale_items=sale_items_with_details,
            cashier_name=sale.cashier.full_name,
            pos_location_name=sale.pos_location.name
        ))
    
    return result