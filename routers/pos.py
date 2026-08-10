from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session,joinedload
from database.database import get_db
from models.user_models import User, UserRole
from models.inventory_models import POSLocation, POSStock, Product
from models.cash_models import Sale, SaleItem, CashRegister
from schemas.inventory_schemas import POSLocationCreate, POSLocation as POSLocationSchema,POSStockWithProduct,POSReturnWithDetails,POSReturnCreate
from schemas.inventory_schemas import WarehouseStock, POSReturn
from schemas.cash_schemas import SaleCreate, Sale as SaleSchema, SaleWithDetails, SaleItemCreate,PaymentMethod
from routers.auth import get_current_user
from typing import Optional, List
from datetime import date, datetime

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
            product=item.product,         # ⭐ ahora existe
            pos_location=item.pos_location  # ⭐ ahora existe
            
        ))
    
    return result

'''@router.post("/{pos_id}/sale", response_model=SaleWithDetails)
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
    
    # === INICIO: Validación y preparación de items ===
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
    
    # === Crear la venta (sin items aún) ===
    db_sale = Sale(
        pos_location_id=pos_id,
        cashier_id=current_user.id,
        total_amount=total_amount,
        cash_received=sale.cash_received,
        change=change
    )
    db.add(db_sale)
    db.flush()  # Para obtener el id de la venta sin commit completo
    
    # === Crear items de venta ===
    sale_items_objects = []
    for item_data in sale_items_data:
        sale_item = SaleItem(
            sale_id=db_sale.id,
            product_id=item_data["product_id"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            subtotal=item_data["subtotal"]
        )
        db.add(sale_item)
        sale_items_objects.append(sale_item)
    
    # === Commit para que se asignen los IDs ===
    db.commit()
    
    # === Refrescar los objetos para obtener IDs generados ===
    db.refresh(db_sale)
    for sale_item in sale_items_objects:
        db.refresh(sale_item)
    
    # === Actualizar stock y caja (después del commit para evitar problemas) ===
    # Actualizar stock en POS
    for item_data in sale_items_data:
        pos_stock = db.query(POSStock).filter(
            POSStock.pos_location_id == pos_id,
            POSStock.product_id == item_data["product_id"]
        ).first()
        if pos_stock:
            pos_stock.quantity -= item_data["quantity"]
    
    # Actualizar caja registradora
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == pos_id
    ).first()
    if cash_register:
        cash_register.current_balance += total_amount
    
    db.commit()
    
    # === Construir respuesta con IDs ya generados ===
    sale_items_with_details = []
    for sale_item in sale_items_objects:
        # Buscar el nombre del producto desde los datos originales
        product_name = next(
            (item["product_name"] for item in sale_items_data 
             if item["product_id"] == sale_item.product_id),
            "Producto"
        )
        sale_items_with_details.append({
            "id": sale_item.id,  # ✅ Ahora es un entero válido
            "sale_id": sale_item.sale_id,
            "product_id": sale_item.product_id,
            "quantity": sale_item.quantity,
            "unit_price": sale_item.unit_price,
            "subtotal": sale_item.subtotal,
            "product_name": product_name
        })
    
    # Construir respuesta final
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

'''
@router.post("/{pos_id}/sale", response_model=SaleWithDetails)
def create_sale(
    pos_id: int,
    sale: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ============================================================
    # 1. VERIFICAR PERMISOS Y POS
    # ============================================================
    if current_user.role == UserRole.CASHIER and current_user.pos_location_id != pos_id:
        raise HTTPException(403, "Access denied to this POS location")

    pos_location = db.query(POSLocation).filter(POSLocation.id == pos_id).first()
    if not pos_location:
        raise HTTPException(404, "POS location not found")

    # ============================================================
    # 2. VALIDAR PAGOS
    # ============================================================
    if not sale.payments:
        raise HTTPException(400, "At least one payment method is required")
    
    total_received = sum(p.amount for p in sale.payments)
    if total_received <= 0:
        raise HTTPException(400, "Total received must be greater than zero")

    # Verificar que los métodos de pago sean válidos
    for payment in sale.payments:
        if payment.method not in [PaymentMethod.CASH, PaymentMethod.TRANSFER]:
            raise HTTPException(400, f"Invalid payment method: {payment.method}")

    # ============================================================
    # 3. CALCULAR TOTAL Y VERIFICAR STOCK
    # ============================================================
    total_amount = 0.0
    sale_items_data = []

    for item in sale.items:
        if item.quantity <= 0:
            raise HTTPException(400, f"Quantity must be greater than zero for product {item.product_id}")

        # Verificar que el producto existe
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(404, f"Product {item.product_id} not found")

        # Si el producto tiene inventario, verificar stock en POS
        if product.has_inventory:
            pos_stock = db.query(POSStock).filter(
                POSStock.pos_location_id == pos_id,
                POSStock.product_id == item.product_id
            ).first()
            if not pos_stock:
                raise HTTPException(400, f"Product {product.name} not available at this POS")
            if pos_stock.quantity < item.quantity:
                raise HTTPException(
                    400,
                    f"Insufficient stock for {product.name}. Available: {pos_stock.quantity}, Requested: {item.quantity}"
                )
        # Si es servicio (sin inventario), no verificar stock

        subtotal = product.price * item.quantity
        total_amount += subtotal

        sale_items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": product.price,
            "subtotal": subtotal,
            "product_name": product.name,
            "has_inventory": product.has_inventory
        })

    # ============================================================
    # 4. VERIFICAR QUE EL PAGO CUBRA EL TOTAL
    # ============================================================
    if total_received < total_amount:
        raise HTTPException(
            400,
            f"Insufficient payment. Total: {total_amount:.2f}, Received: {total_received:.2f}"
        )

    # ============================================================
    # 5. CALCULAR CAMBIO (SOLO SI HAY EFECTIVO)
    # ============================================================
    cash_payment = next((p.amount for p in sale.payments if p.method == PaymentMethod.CASH), 0.0)
    transfer_payment = next((p.amount for p in sale.payments if p.method == PaymentMethod.TRANSFER), 0.0)

    # El cambio solo se da si hay pago en efectivo y el total recibido supera el total
    change = 0.0
    if cash_payment > 0:
        change = total_received - total_amount
        # El cambio no puede ser negativo (ya validamos que total_received >= total_amount)
        # Pero si solo hay transferencia, change se queda en 0

    # ============================================================
    # 6. CREAR LA VENTA
    # ============================================================
    payment_dict = {p.method.value: p.amount for p in sale.payments}

    db_sale = Sale(
        pos_location_id=pos_id,
        cashier_id=current_user.id,
        total_amount=total_amount,
        payment_details=payment_dict,
        change=change,
        status="completed"
    )
    db.add(db_sale)
    db.flush()  # ⬅️ Para obtener el ID de la venta

    # ============================================================
    # 7. CREAR ITEMS Y ACTUALIZAR STOCK
    # ============================================================
    sale_items_created = []

    for item_data in sale_items_data:
        sale_item = SaleItem(
            sale_id=db_sale.id,
            product_id=item_data["product_id"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            subtotal=item_data["subtotal"]
        )
        db.add(sale_item)
        db.flush()  # ⬅️ Para obtener el ID del item

        # Actualizar stock en POS solo si el producto tiene inventario
        if item_data["has_inventory"]:
            pos_stock = db.query(POSStock).filter(
                POSStock.pos_location_id == pos_id,
                POSStock.product_id == item_data["product_id"]
            ).first()
            if pos_stock:
                pos_stock.quantity -= item_data["quantity"]

        sale_items_created.append(sale_item)

    # ============================================================
    # 8. ACTUALIZAR CAJA REGISTRADORA (SOLO EFECTIVO)
    # ============================================================
    if cash_payment > 0:
        cash_register = db.query(CashRegister).filter(
            CashRegister.pos_location_id == pos_id
        ).first()
        if cash_register:
            cash_register.current_balance += cash_payment

    # ============================================================
    # 9. CONFIRMAR TRANSACCIÓN
    # ============================================================
    db.commit()

    # Refrescar la venta y los items para tener todos los datos actualizados
    db.refresh(db_sale)
    for item in sale_items_created:
        db.refresh(item)

    # ============================================================
    # 10. CONSTRUIR RESPUESTA
    # ============================================================
    return SaleWithDetails(
        id=db_sale.id,
        pos_location_id=db_sale.pos_location_id,
        cashier_id=db_sale.cashier_id,
        total_amount=db_sale.total_amount,
        payment_details=db_sale.payment_details,
        change=db_sale.change,
        sale_date=db_sale.sale_date,
        status=db_sale.status,
        cancelled_by=db_sale.cancelled_by,
        cancelled_at=db_sale.cancelled_at,
        cancellation_reason=db_sale.cancellation_reason,
        sale_items=[
            SaleItemWithProduct(
                id=item.id,
                sale_id=item.sale_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                product_name=next(
                    (d["product_name"] for d in sale_items_data if d["product_id"] == item.product_id),
                    "Producto"
                )
            ) for item in sale_items_created
        ],
        cashier_name=current_user.full_name,
        pos_location_name=pos_location.name,
        canceller_name=None
    )
# ============================================================
# 1. LISTAR VENTAS CANCELADAS
# ============================================================
@router.get("/sales/cancelled", response_model=List[SaleWithDetails])
def list_cancelled_sales(
    pos_location_id: Optional[int] = Query(None, description="Filtrar por POS"),
    cashier_id: Optional[int] = Query(None, description="Filtrar por cajero"),
    start_date: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Sale).options(
        joinedload(Sale.sale_items).joinedload(SaleItem.product),
        joinedload(Sale.cashier),
        joinedload(Sale.pos_location),
        joinedload(Sale.canceller)
    ).filter(Sale.status == "cancelled")

    if pos_location_id:
        query = query.filter(Sale.pos_location_id == pos_location_id)
    if cashier_id:
        query = query.filter(Sale.cashier_id == cashier_id)
    if start_date:
        query = query.filter(Sale.sale_date >= start_date)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Sale.sale_date <= end_datetime)

    sales = query.order_by(Sale.sale_date.desc()).offset(skip).limit(limit).all()

    result = []
    for sale in sales:
        result.append(SaleWithDetails(
            id=sale.id,
            pos_location_id=sale.pos_location_id,
            cashier_id=sale.cashier_id,
            total_amount=sale.total_amount,
            payment_details=sale.payment_details,
            change=sale.change,
            sale_date=sale.sale_date,
            status=sale.status,
            cancelled_by=sale.cancelled_by,
            cancelled_at=sale.cancelled_at,
            cancellation_reason=sale.cancellation_reason,
            sale_items=[
                SaleItemWithProduct(
                    id=item.id,
                    sale_id=item.sale_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                    product_name=item.product.name
                ) for item in sale.sale_items
            ],
            cashier_name=sale.cashier.full_name,
            pos_location_name=sale.pos_location.name,
            canceller_name=sale.canceller.full_name if sale.canceller else None
        ))
    return result

# ============================================================
# 2. LISTAR VENTAS ACTIVAS (NO CANCELADAS)
# ============================================================
@router.get("/sales/active", response_model=List[SaleWithDetails])
def list_active_sales(
    pos_location_id: Optional[int] = Query(None, description="Filtrar por POS"),
    cashier_id: Optional[int] = Query(None, description="Filtrar por cajero"),
    start_date: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Sale).options(
        joinedload(Sale.sale_items).joinedload(SaleItem.product),
        joinedload(Sale.cashier),
        joinedload(Sale.pos_location),
        joinedload(Sale.canceller)
    ).filter(Sale.status == "completed")

    if pos_location_id:
        query = query.filter(Sale.pos_location_id == pos_location_id)
    if cashier_id:
        query = query.filter(Sale.cashier_id == cashier_id)
    if start_date:
        query = query.filter(Sale.sale_date >= start_date)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Sale.sale_date <= end_datetime)

    sales = query.order_by(Sale.sale_date.desc()).offset(skip).limit(limit).all()

    result = []
    for sale in sales:
        result.append(SaleWithDetails(
            id=sale.id,
            pos_location_id=sale.pos_location_id,
            cashier_id=sale.cashier_id,
            total_amount=sale.total_amount,
            payment_details=sale.payment_details,
            change=sale.change,
            sale_date=sale.sale_date,
            status=sale.status,
            cancelled_by=sale.cancelled_by,
            cancelled_at=sale.cancelled_at,
            cancellation_reason=sale.cancellation_reason,
            sale_items=[
                SaleItemWithProduct(
                    id=item.id,
                    sale_id=item.sale_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                    product_name=item.product.name
                ) for item in sale.sale_items
            ],
            cashier_name=sale.cashier.full_name,
            pos_location_name=sale.pos_location.name,
            canceller_name=sale.canceller.full_name if sale.canceller else None
        ))
    return result

from typing import Optional
from schemas.cash_schemas import SaleItemWithProduct
from datetime import date

@router.get("/sales/active", response_model=List[SaleWithDetails])
def list_active_sales(
    pos_location_id: Optional[int] = Query(None, description="Filtrar por POS"),
    cashier_id: Optional[int] = Query(None, description="Filtrar por cajero"),
    start_date: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Construir consulta base: solo ventas activas (no canceladas)
    query = db.query(Sale).options(
        joinedload(Sale.sale_items).joinedload(SaleItem.product),
        joinedload(Sale.cashier),
        joinedload(Sale.pos_location),
        joinedload(Sale.canceller)
    ).filter(Sale.status == "completed")

    # Aplicar filtros (igual que el anterior)
    if pos_location_id:
        query = query.filter(Sale.pos_location_id == pos_location_id)
    if cashier_id:
        query = query.filter(Sale.cashier_id == cashier_id)
    if start_date:
        query = query.filter(Sale.sale_date >= start_date)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Sale.sale_date <= end_datetime)

    sales = query.order_by(Sale.sale_date.desc()).offset(skip).limit(limit).all()

    # Construir respuesta
    result = []
    for sale in sales:
        result.append(SaleWithDetails(
            id=sale.id,
            pos_location_id=sale.pos_location_id,
            cashier_id=sale.cashier_id,
            total_amount=sale.total_amount,
            payment_details=sale.payment_details,  # ⬅️ NUEVO
            change=sale.change,
            sale_date=sale.sale_date,
            status=sale.status,
            cancelled_by=sale.cancelled_by,
            cancelled_at=sale.cancelled_at,
            cancellation_reason=sale.cancellation_reason,
            sale_items=[
                SaleItemWithProduct(
                    id=item.id,
                    sale_id=item.sale_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                    product_name=item.product.name
                ) for item in sale.sale_items
            ],
            cashier_name=sale.cashier.full_name,
            pos_location_name=sale.pos_location.name,
            canceller_name=sale.canceller.full_name if sale.canceller else None
        ))
    
    return result

# 3. OBTENER DETALLE DE UNA VENTA POR ID
# ============================================================
@router.get("/sales/{sale_id}", response_model=SaleWithDetails)
def get_sale_details(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sale = db.query(Sale).options(
        joinedload(Sale.sale_items).joinedload(SaleItem.product),
        joinedload(Sale.cashier),
        joinedload(Sale.pos_location),
        joinedload(Sale.canceller)
    ).filter(Sale.id == sale_id).first()

    if not sale:
        raise HTTPException(404, "Sale not found")

    if current_user.role != UserRole.ADMIN and current_user.id != sale.cashier_id:
        raise HTTPException(403, "Access denied")

    return SaleWithDetails(
        id=sale.id,
        pos_location_id=sale.pos_location_id,
        cashier_id=sale.cashier_id,
        total_amount=sale.total_amount,
        payment_details=sale.payment_details,
        change=sale.change,
        sale_date=sale.sale_date,
        status=sale.status,
        cancelled_by=sale.cancelled_by,
        cancelled_at=sale.cancelled_at,
        cancellation_reason=sale.cancellation_reason,
        sale_items=[
            SaleItemWithProduct(
                id=item.id,
                sale_id=item.sale_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                product_name=item.product.name
            ) for item in sale.sale_items
        ],
        cashier_name=sale.cashier.full_name,
        pos_location_name=sale.pos_location.name,
        canceller_name=sale.canceller.full_name if sale.canceller else None
    )



#return prod 
@router.post("/{pos_id}/return", response_model=POSReturnWithDetails)
def create_pos_return(
    pos_id: int,
    return_data: POSReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Solo ADMIN o WAREHOUSE_MANAGER pueden autorizar devoluciones
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(403, "Only admin or warehouse manager can authorize returns")

    # Verificar que el POS existe
    pos = db.query(POSLocation).filter(POSLocation.id == pos_id).first()
    if not pos:
        raise HTTPException(404, "POS location not found")

    # Verificar que el producto existe
    product = db.query(Product).filter(Product.id == return_data.product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")

    # Verificar stock en POS
    pos_stock = db.query(POSStock).filter(
        POSStock.pos_location_id == pos_id,
        POSStock.product_id == return_data.product_id
    ).first()
    if not pos_stock or pos_stock.quantity < return_data.quantity:
        raise HTTPException(400, f"Insufficient stock in POS. Available: {pos_stock.quantity if pos_stock else 0}")

    # Crear la devolución (estado pending)
    db_return = POSReturn(
        pos_location_id=pos_id,
        product_id=return_data.product_id,
        quantity=return_data.quantity,
        reason=return_data.reason.value,
        reason_text=return_data.reason_text,
        notes=return_data.notes,
        authorized_by=current_user.id,
        status="pending"
    )
    db.add(db_return)
    db.commit()
    db.refresh(db_return)

    # Construir respuesta
    return POSReturnWithDetails(
        id=db_return.id,
        pos_location_id=db_return.pos_location_id,
        product_id=db_return.product_id,
        quantity=db_return.quantity,
        reason=db_return.reason,
        reason_text=db_return.reason_text,
        notes=db_return.notes,
        authorized_by=db_return.authorized_by,
        authorized_at=db_return.authorized_at,
        status=db_return.status,
        completed_at=db_return.completed_at,
        pos_location_name=pos.name,
        product_name=product.name,
        authorizer_name=current_user.full_name
    )

#aprobar solcitud de retorno 
@router.put("/return/{return_id}/complete", response_model=POSReturnWithDetails)
def complete_pos_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Solo ADMIN o WAREHOUSE_MANAGER
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(403, "Only admin or warehouse manager can complete returns")

    db_return = db.query(POSReturn).filter(POSReturn.id == return_id).first()
    if not db_return:
        raise HTTPException(404, "Return not found")

    if db_return.status != "pending":
        raise HTTPException(400, f"Return already {db_return.status}")

    # Verificar stock en POS (nuevamente, por si cambió)
    pos_stock = db.query(POSStock).filter(
        POSStock.pos_location_id == db_return.pos_location_id,
        POSStock.product_id == db_return.product_id
    ).first()
    if not pos_stock or pos_stock.quantity < db_return.quantity:
        raise HTTPException(400, f"Insufficient stock in POS. Available: {pos_stock.quantity if pos_stock else 0}")

    # 1. Restar stock en POS
    pos_stock.quantity -= db_return.quantity

    # 2. Sumar stock en warehouse
    warehouse_stock = db.query(WarehouseStock).filter(
        WarehouseStock.product_id == db_return.product_id
    ).first()
    if warehouse_stock:
        warehouse_stock.quantity += db_return.quantity
    else:
        # Si no existe, crear (por si acaso)
        warehouse_stock = WarehouseStock(
            product_id=db_return.product_id,
            quantity=db_return.quantity,
            min_stock=10
        )
        db.add(warehouse_stock)

    # 3. Marcar como completada
    db_return.status = "completed"
    db_return.completed_at = datetime.now()

    db.commit()
    db.refresh(db_return)

    # Obtener datos adicionales para respuesta
    pos = db.query(POSLocation).filter(POSLocation.id == db_return.pos_location_id).first()
    product = db.query(Product).filter(Product.id == db_return.product_id).first()
    authorizer = db.query(User).filter(User.id == db_return.authorized_by).first()

    return POSReturnWithDetails(
        id=db_return.id,
        pos_location_id=db_return.pos_location_id,
        product_id=db_return.product_id,
        quantity=db_return.quantity,
        reason=db_return.reason,
        reason_text=db_return.reason_text,
        notes=db_return.notes,
        authorized_by=db_return.authorized_by,
        authorized_at=db_return.authorized_at,
        status=db_return.status,
        completed_at=db_return.completed_at,
        pos_location_name=pos.name if pos else "Unknown",
        product_name=product.name if product else "Unknown",
        authorizer_name=authorizer.full_name if authorizer else "Unknown"
    )
    
    
#LIstar Devoluciones 
@router.get("/returns", response_model=List[POSReturnWithDetails])
def list_pos_returns(
    pos_location_id: Optional[int] = Query(None, description="Filtrar por POS"),
    product_id: Optional[int] = Query(None, description="Filtrar por producto"),
    status: Optional[str] = Query(None, description="Filtrar por estado (pending, completed, rejected)"),
    start_date: Optional[date] = Query(None, description="Fecha inicio"),
    end_date: Optional[date] = Query(None, description="Fecha fin"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Solo ADMIN o WAREHOUSE_MANAGER pueden ver devoluciones
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(403, "Access denied")

    query = db.query(POSReturn).options(
        joinedload(POSReturn.pos_location),
        joinedload(POSReturn.product),
        joinedload(POSReturn.authorizer)
    )

    if pos_location_id:
        query = query.filter(POSReturn.pos_location_id == pos_location_id)
    if product_id:
        query = query.filter(POSReturn.product_id == product_id)
    if status:
        query = query.filter(POSReturn.status == status)
    if start_date:
        query = query.filter(POSReturn.authorized_at >= start_date)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.filter(POSReturn.authorized_at <= end_dt)

    returns = query.order_by(POSReturn.authorized_at.desc()).offset(skip).limit(limit).all()

    result = []
    for r in returns:
        result.append(POSReturnWithDetails(
            id=r.id,
            pos_location_id=r.pos_location_id,
            product_id=r.product_id,
            quantity=r.quantity,
            reason=r.reason,
            reason_text=r.reason_text,
            notes=r.notes,
            authorized_by=r.authorized_by,
            authorized_at=r.authorized_at,
            status=r.status,
            completed_at=r.completed_at,
            pos_location_name=r.pos_location.name,
            product_name=r.product.name,
            authorizer_name=r.authorizer.full_name
        ))
    return result

# CANCELAR venta

from datetime import datetime

@router.put("/{pos_id}/sale/{sale_id}/cancel", response_model=SaleWithDetails)
def cancel_sale(
    pos_id: int,
    sale_id: int,
    reason: str = Query(..., description="Motivo de la cancelación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar permisos (solo admin o el mismo cajero)
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        if current_user.role != UserRole.CASHIER:
            raise HTTPException(403, "No tienes permisos para cancelar ventas")
        # Si es cajero, solo puede cancelar sus propias ventas
        sale = db.query(Sale).filter(Sale.id == sale_id, Sale.cashier_id == current_user.id).first()
        if not sale:
            raise HTTPException(404, "Venta no encontrada o no te pertenece")
    else:
        # Admin puede cancelar cualquier venta
        sale = db.query(Sale).filter(Sale.id == sale_id).first()
        if not sale:
            raise HTTPException(404, "Venta no encontrada")

    # Verificar que la venta no esté ya cancelada
    if sale.status == "cancelled":
        raise HTTPException(400, "Esta venta ya está cancelada")

    # Verificar que la venta pertenezca al POS correcto
    if sale.pos_location_id != pos_id:
        raise HTTPException(400, "La venta no pertenece a este POS")

    # Revertir stock en POS (sumar las cantidades)
    for item in sale.sale_items:
        pos_stock = db.query(POSStock).filter(
            POSStock.pos_location_id == pos_id,
            POSStock.product_id == item.product_id
        ).first()
        if pos_stock:
            pos_stock.quantity += item.quantity
        else:
            # Si no existe registro de stock (caso raro), lo creamos
            pos_stock = POSStock(
                pos_location_id=pos_id,
                product_id=item.product_id,
                quantity=item.quantity
            )
            db.add(pos_stock)

    # Revertir el balance de la caja registradora
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == pos_id
    ).first()
    if cash_register:
        cash_register.current_balance -= sale.total_amount

    # Marcar la venta como cancelada
    sale.status = "cancelled"
    sale.cancelled_by = current_user.id
    sale.cancelled_at = datetime.now()
    sale.cancellation_reason = reason

    db.commit()

    # Recargar con relaciones para la respuesta
    result = db.query(Sale).options(
        joinedload(Sale.sale_items).joinedload(SaleItem.product),
        joinedload(Sale.cashier),
        joinedload(Sale.pos_location),
        joinedload(Sale.canceller)
    ).filter(Sale.id == sale_id).first()

    # Construir respuesta
    return SaleWithDetails(
        id=result.id,
        pos_location_id=result.pos_location_id,
        cashier_id=result.cashier_id,
        total_amount=result.total_amount,
        payment_details=sale.payment_details,
        change=result.change,
        sale_date=result.sale_date,
        status=result.status,
        cancelled_by=result.cancelled_by,
        cancelled_at=result.cancelled_at,
        cancellation_reason=result.cancellation_reason,
        sale_items=[
            SaleItemWithProduct(
                id=item.id,
                sale_id=item.sale_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                product_name=item.product.name
            ) for item in result.sale_items
        ],
        cashier_name=result.cashier.full_name,
        pos_location_name=result.pos_location.name,
        canceller_name=result.canceller.full_name if result.canceller else None
    )
    
    
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
            payment_details=sale.payment_details,
            change=sale.change,
            sale_date=sale.sale_date,
            sale_items=sale_items_with_details,
            cashier_name=sale.cashier.full_name,
            pos_location_name=sale.pos_location.name
        ))
    
    return result

# ============================================================
# 3. OBTENER DETALLE DE UNA VENTA POR ID
# ============================================================
@router.get("/sales/{sale_id}", response_model=SaleWithDetails)
def get_sale_details(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sale = db.query(Sale).options(
        joinedload(Sale.sale_items).joinedload(SaleItem.product),
        joinedload(Sale.cashier),
        joinedload(Sale.pos_location),
        joinedload(Sale.canceller)
    ).filter(Sale.id == sale_id).first()

    if not sale:
        raise HTTPException(404, "Sale not found")

    if current_user.role != UserRole.ADMIN and current_user.id != sale.cashier_id:
        raise HTTPException(403, "Access denied")

    return SaleWithDetails(
        id=sale.id,
        pos_location_id=sale.pos_location_id,
        cashier_id=sale.cashier_id,
        total_amount=sale.total_amount,
        payment_details=sale.payment_details,
        change=sale.change,
        sale_date=sale.sale_date,
        status=sale.status,
        cancelled_by=sale.cancelled_by,
        cancelled_at=sale.cancelled_at,
        cancellation_reason=sale.cancellation_reason,
        sale_items=[
            SaleItemWithProduct(
                id=item.id,
                sale_id=item.sale_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                product_name=item.product.name
            ) for item in sale.sale_items
        ],
        cashier_name=sale.cashier.full_name,
        pos_location_name=sale.pos_location.name,
        canceller_name=sale.canceller.full_name if sale.canceller else None
    )
