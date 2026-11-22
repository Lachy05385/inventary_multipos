from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.database import get_db
from models.user_models import User, UserRole
from models.inventory_models import POSLocation, POSStock, Product
from models.cash_models import Sale, SaleItem, CashRegister
from schemas.inventory_schemas import POSLocationCreate, POSLocation as POSLocationSchema, POSStockWithProduct
from schemas.cash_schemas import SaleCreate, SaleItemBase, SaleWithDetails, SaleItemCreate,SaleResponse
from routers.auth import get_current_user
from datetime import datetime, time
from schemas.cash_schemas import (
    SaleCreate,
    SaleResponse,
    BatchSaleClose,
    BatchSaleResponse,
    SaleItemCreate,
)

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
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
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
            product=item.product,         # ⭐ ahora existe
            pos_location=item.pos_location  # ⭐ ahora existe
            
        ))
    
    return result

@router.post("/{pos_id}/sale", response_model=SaleResponse)
def create_sale(
    pos_id: int,
    sale: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Validar POS
    pos = db.query(POSLocation).filter(POSLocation.id == pos_id).first()
    if not pos:
        raise HTTPException(404, "POS no encontrado")

    # 2. Permisos
    if current_user.role == UserRole.CASHIER and current_user.pos_location_id != pos_id:
        raise HTTPException(403, "No tienes acceso a este POS")

    # 3. Validar stock y calcular total
    total = 0.0
    items_data = []
    for item in sale.items:
        pos_stock = db.query(POSStock).filter(
            POSStock.pos_location_id == pos_id,
            POSStock.product_id == item.product_id,
        ).first()
        if not pos_stock or pos_stock.quantity < item.quantity:
            prod = db.query(Product).filter(Product.id == item.product_id).first()
            raise HTTPException(
                400,
                f"Stock insuficiente para '{prod.name if prod else item.product_id}'"
            )

        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(404, f"Producto {item.product_id} no encontrado")

        subtotal = product.price * item.quantity
        total += subtotal
        items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": product.price,
            "subtotal": subtotal,
            "product_name": product.name,
        })

    # 4. Validar pagos
    total_paid = sale.cash_amount + sale.transfer_amount
    if total_paid < total:
        raise HTTPException(
            400,
            f"Pago insuficiente. Total: {total}, recibido: {total_paid}"
        )
    change = round(total_paid - total, 2)

    # 5. Crear venta
    db_sale = Sale(
        pos_location_id=pos_id,
        cashier_id=current_user.id,
        total_amount=total,
        cash_amount=sale.cash_amount,
        transfer_amount=sale.transfer_amount,
        change_given=change,
        sale_type="individual",
        notes=sale.notes,
    )
    db.add(db_sale)
    db.flush()

    # 6. Items y stock
    for item_data in items_data:
        db.add(SaleItem(
            sale_id=db_sale.id,
            product_id=item_data["product_id"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            subtotal=item_data["subtotal"],
        ))
        pos_stock = db.query(POSStock).filter(
            POSStock.pos_location_id == pos_id,
            POSStock.product_id == item_data["product_id"],
        ).first()
        pos_stock.quantity -= item_data["quantity"]

    # 7. Actualizar caja (solo efectivo)
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == pos_id
    ).first()
    if cash_register:
        cash_register.current_balance += sale.cash_amount

    db.commit()
    db.refresh(db_sale)

    # 8. Respuesta
    return {
        "id": db_sale.id,
        "pos_location_id": db_sale.pos_location_id,
        "cashier_id": db_sale.cashier_id,
        "total_amount": db_sale.total_amount,
        "cash_amount": db_sale.cash_amount,
        "transfer_amount": db_sale.transfer_amount,
        "change_given": db_sale.change_given,
        "sale_type": db_sale.sale_type,
        "notes": db_sale.notes,
        "sale_date": db_sale.sale_date,
        "items": items_data,
        "cashier_name": current_user.full_name,
        "pos_location_name": pos.name,
    }

from datetime import datetime, time
from sqlalchemy import func

@router.post("/{pos_id}/batch-sale")
def create_batch_sale(
    pos_id: int,
    data: BatchSaleClose,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validar POS y permisos
    pos = db.query(POSLocation).filter(POSLocation.id == pos_id).first()
    if not pos:
        raise HTTPException(404, "POS no encontrado")
    if current_user.role == UserRole.CASHIER and current_user.pos_location_id != pos_id:
        raise HTTPException(403, "No tienes acceso a este POS")

    # Rango del día
    today = datetime.today().date()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)

    # Suma de ventas individuales del día
    total_individual = (
        db.query(func.sum(Sale.total_amount))
        .filter(
            Sale.pos_location_id == pos_id,
            Sale.sale_date >= start,
            Sale.sale_date <= end,
            Sale.sale_type == "individual",
        )
        .scalar()
    ) or 0.0

    # Lo que el cajero declara al cierre
    total_declarado = data.cash_amount + data.transfer_amount
    diferencia = round(total_declarado - total_individual, 2)

    # Crear registro de cierre (tipo batch)
    db_sale = Sale(
        pos_location_id=pos_id,
        cashier_id=current_user.id,
        total_amount=total_declarado,
        cash_amount=data.cash_amount,
        transfer_amount=data.transfer_amount,
        change_given=0.0,
        sale_type="batch",
        notes=f"Cierre de caja. Diferencia: {diferencia}",
    )
    db.add(db_sale)

    # Actualizar caja con el efectivo declarado
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == pos_id
    ).first()
    if cash_register:
        cash_register.current_balance += data.cash_amount

    db.commit()
    db.refresh(db_sale)

    return {
        "id": db_sale.id,
        "pos_location_id": pos_id,
        "total_amount": db_sale.total_amount,
        "cash_amount": db_sale.cash_amount,
        "transfer_amount": db_sale.transfer_amount,
        "sale_type": "batch",
        "sale_date": db_sale.sale_date,
        "total_individual_sales": total_individual,
        "difference": diferencia,
        "message": "Cierre registrado. Diferencia: " + str(diferencia) if diferencia != 0 else "Cierre perfecto",
    }

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

@router.get("/{pos_id}/cash-summary")
def get_cash_summary(
    pos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validar permisos
    if current_user.role == UserRole.CASHIER and current_user.pos_location_id != pos_id:
        raise HTTPException(403, "No tienes acceso a este POS")
    pos = db.query(POSLocation).filter(POSLocation.id == pos_id).first()
    if not pos:
        raise HTTPException(404, "POS no encontrado")

    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == pos_id
    ).first()

    # Totales del día (opcional)
    from datetime import datetime, time
    today = datetime.today().date()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)

    sales_today = (
        db.query(
            func.sum(Sale.total_amount).label("total"),
            func.sum(Sale.cash_amount).label("cash"),
            func.sum(Sale.transfer_amount).label("transfer"),
        )
        .filter(
            Sale.pos_location_id == pos_id,
            Sale.sale_date >= start,
            Sale.sale_date <= end,
        )
        .first()
    )

    return {
        "pos_location_id": pos_id,
        "pos_location_name": pos.name,
        "current_balance": cash_register.current_balance if cash_register else 0.0,
        "today": {
            "total_sales": float(sales_today.total or 0),
            "cash": float(sales_today.cash or 0),
            "transfer": float(sales_today.transfer or 0),
        },
    }



@router.put("/locations/{pos_id}", response_model=POSLocationSchema)
def update_pos_location(
    pos_id: int,
    location: POSLocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    pos = db.query(POSLocation).filter(POSLocation.id == pos_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="POS location not found")

    pos.name = location.name
    pos.address = location.address
    db.commit()
    db.refresh(pos)
    return pos


@router.delete("/locations/{pos_id}")
def delete_pos_location(
    pos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    pos = db.query(POSLocation).filter(POSLocation.id == pos_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="POS location not found")

    # ⚠️ Verificar que no tenga ventas
    from models.cash_models import Sale
    ventas = db.query(Sale).filter(Sale.pos_location_id == pos_id).count()
    if ventas > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar: tiene {ventas} venta(s) asociada(s)")

    # Soft delete
    pos.is_active = False
    db.commit()
    return {"message": f"POS '{pos.name}' desactivado"}