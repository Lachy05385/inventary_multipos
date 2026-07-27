from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from database.database import get_db
from models.user_models import User, UserRole
from models.inventory_models import Supplier, PurchaseEntry, PurchaseItem, Product, WarehouseStock
from schemas.inventory_schemas import (
    SupplierCreate, SupplierUpdate, Supplier as SupplierSchema,
    PurchaseEntryCreate, PurchaseEntryUpdate, PurchaseEntryWithDetails,
    PurchaseItemCreate
)

from routers.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

def get_admin_or_warehouse_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

# ========== SUPPLIERS CRUD ==========
@router.post("/", response_model=SupplierSchema)
def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    print("Alta a Proveedor ")
    print("current user", current_user)
    print("="*50)
    print(supplier.code," ", supplier.name )
    print(supplier.contact_phone, " ",supplier.contact_email)
    print("="*50)
    
    # Verificar código único
    existing = db.query(Supplier).filter(Supplier.code == supplier.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier code already exists")
    
    db_supplier = Supplier(
        name=supplier.name,
        code=supplier.code,
        contract_number=supplier.contract_number,
        document_type=supplier.document_type.value,
        contact_phone=supplier.contact_phone,
        contact_email=supplier.contact_email,
        address=supplier.address
    )
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@router.get("/", response_model=List[SupplierSchema])
def read_suppliers(
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None, description="Search by name or code"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    query = db.query(Supplier)
    if search:
        query = query.filter(
            (Supplier.name.ilike(f"%{search}%")) |
            (Supplier.code.ilike(f"%{search}%"))
        )
    suppliers = query.offset(skip).limit(limit).all()
    return suppliers

@router.get("/{supplier_id}", response_model=SupplierSchema)
def read_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@router.put("/{supplier_id}", response_model=SupplierSchema)
def update_supplier(
    supplier_id: int,
    supplier_update: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier_update.model_dump(exclude_unset=True)
    if 'document_type' in update_data and update_data['document_type']:
        update_data['document_type'] = update_data['document_type'].value
    
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    db.commit()
    db.refresh(supplier)
    return supplier

@router.delete("/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    # Verificar si tiene entradas de compra
    if supplier.purchase_entries:
        raise HTTPException(status_code=400, detail="Cannot delete supplier with associated purchase entries")
    db.delete(supplier)
    db.commit()
    return {"detail": "Supplier deleted"}

# ========== PURCHASE ENTRIES ==========
@router.post("/entries", response_model=PurchaseEntryWithDetails)
def create_purchase_entry(
    entry: PurchaseEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    # Verificar proveedor
    supplier = db.query(Supplier).filter(Supplier.id == entry.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Calcular total
    total = 0
    items_data = []
    for item in entry.items:
        # Verificar producto
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        # Calcular subtotal
        subtotal = item.quantity * item.unit_price - item.discount
        total += subtotal
        items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "subtotal": subtotal,
            "discount": item.discount
        })
    
    # Crear entrada
    db_entry = PurchaseEntry(
        supplier_id=entry.supplier_id,
        total_amount=total,
        paid_amount=0,
        status="pending",
        notes=entry.notes
    )
    db.add(db_entry)
    db.flush()  # para obtener el id
    
    # Crear items
    for data in items_data:
        item = PurchaseItem(
            purchase_entry_id=db_entry.id,
            **data
        )
        db.add(item)
        # Actualizar stock en almacén (sumar cantidad)
        warehouse = db.query(WarehouseStock).filter(WarehouseStock.product_id == data["product_id"]).first()
        if warehouse:
            warehouse.quantity += data["quantity"]
        else:
            # Si el producto no tiene stock, crear uno (solo si tiene inventario)
            product = db.query(Product).filter(Product.id == data["product_id"]).first()
            if product and product.has_inventory:
                new_stock = WarehouseStock(product_id=data["product_id"], quantity=data["quantity"], min_stock=10)
                db.add(new_stock)
    
    db.commit()
    db.refresh(db_entry)
    
    # Cargar relaciones para la respuesta
    result = db.query(PurchaseEntry).options(
        joinedload(PurchaseEntry.supplier),
        joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
    ).filter(PurchaseEntry.id == db_entry.id).first()
    
    return result

@router.get("/entries", response_model=List[PurchaseEntryWithDetails])
def read_purchase_entries(
    skip: int = 0,
    limit: int = 100,
    supplier_id: int = Query(None, description="Filter by supplier"),
    status: str = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    query = db.query(PurchaseEntry).options(
        joinedload(PurchaseEntry.supplier),
        joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
    )
    if supplier_id:
        query = query.filter(PurchaseEntry.supplier_id == supplier_id)
    if status:
        query = query.filter(PurchaseEntry.status == status)
    
    entries = query.order_by(PurchaseEntry.entry_date.desc()).offset(skip).limit(limit).all()
    return entries

from datetime import date
from typing import Optional

@router.get("/entries/summary")
def get_purchase_summary(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    supplier_id: Optional[int] = Query(None, description="Filter by supplier ID (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    """
    Obtiene un resumen de las entradas de productos en un período.
    Agrupa por proveedor y por producto.
    """
    # Construir consulta base
    query = db.query(PurchaseEntry).filter(
        PurchaseEntry.entry_date >= start_date,
        PurchaseEntry.entry_date <= end_date
    )

    if supplier_id:
        query = query.filter(PurchaseEntry.supplier_id == supplier_id)

    # Obtener todas las entradas con sus items y relaciones
    entries = query.options(
        joinedload(PurchaseEntry.supplier),
        joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
    ).all()

    # Estructuras para acumular
    summary = {
        "total_entries": len(entries),
        "total_amount": 0.0,
        "total_paid": 0.0,
        "total_balance": 0.0,
        "suppliers": {},
        "products": {}
    }

    for entry in entries:
        # Totales generales
        summary["total_amount"] += entry.total_amount
        summary["total_paid"] += entry.paid_amount
        summary["total_balance"] += (entry.total_amount - entry.paid_amount)

        # Agrupar por proveedor
        supplier_name = entry.supplier.name
        if supplier_name not in summary["suppliers"]:
            summary["suppliers"][supplier_name] = {
                "supplier_id": entry.supplier.id,
                "total_amount": 0.0,
                "total_paid": 0.0,
                "balance": 0.0,
                "entries_count": 0
            }
        summary["suppliers"][supplier_name]["total_amount"] += entry.total_amount
        summary["suppliers"][supplier_name]["total_paid"] += entry.paid_amount
        summary["suppliers"][supplier_name]["balance"] += (entry.total_amount - entry.paid_amount)
        summary["suppliers"][supplier_name]["entries_count"] += 1

        # Agrupar por producto (dentro de cada entrada)
        for item in entry.items:
            product_name = item.product.name
            if product_name not in summary["products"]:
                summary["products"][product_name] = {
                    "product_id": item.product_id,
                    "total_quantity": 0,
                    "total_purchased": 0.0,
                    "average_price": 0.0
                }
            summary["products"][product_name]["total_quantity"] += item.quantity
            summary["products"][product_name]["total_purchased"] += item.subtotal

    # Calcular precio promedio por producto
    for prod in summary["products"].values():
        if prod["total_quantity"] > 0:
            prod["average_price"] = prod["total_purchased"] / prod["total_quantity"]

    # Convertir a lista para mejor serialización (opcional)
    summary["suppliers"] = [
        {
            "name": name,
            **data
        } for name, data in summary["suppliers"].items()
    ]
    summary["products"] = [
        {
            "name": name,
            **data
        } for name, data in summary["products"].items()
    ]

    return summary




@router.get("/entries/{entry_id}", response_model=PurchaseEntryWithDetails)
def read_purchase_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    entry = db.query(PurchaseEntry).options(
        joinedload(PurchaseEntry.supplier),
        joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
    ).filter(PurchaseEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Purchase entry not found")
    return entry

@router.put("/entries/{entry_id}", response_model=PurchaseEntryWithDetails)
def update_purchase_entry(
    entry_id: int,
    entry_update: PurchaseEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    entry = db.query(PurchaseEntry).filter(PurchaseEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Purchase entry not found")
    
    # Si se actualiza el paid_amount, validar que no exceda el total
    if entry_update.paid_amount is not None:
        if entry_update.paid_amount > entry.total_amount:
            raise HTTPException(status_code=400, detail="Paid amount cannot exceed total amount")
        entry.paid_amount = entry_update.paid_amount
        # Actualizar estado automáticamente
        if entry.paid_amount == 0:
            entry.status = "pending"
        elif entry.paid_amount < entry.total_amount:
            entry.status = "partial"
        else:
            entry.status = "paid"
    
    if entry_update.notes is not None:
        entry.notes = entry_update.notes
    
    if entry_update.status is not None:
        entry.status = entry_update.status.value
    
    db.commit()
    db.refresh(entry)
    
    # Recargar con relaciones
    result = db.query(PurchaseEntry).options(
        joinedload(PurchaseEntry.supplier),
        joinedload(PurchaseEntry.items).joinedload(PurchaseItem.product)
    ).filter(PurchaseEntry.id == entry_id).first()
    return result

# ========== OBTENER DEUDA DE UN PROVEEDOR ==========
@router.get("/{supplier_id}/debt")
def get_supplier_debt(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Sumar total de todas las entradas pendientes y parciales
    entries = db.query(PurchaseEntry).filter(
        PurchaseEntry.supplier_id == supplier_id,
        PurchaseEntry.status.in_(["pending", "partial"])
    ).all()
    
    total_debt = sum(entry.total_amount - entry.paid_amount for entry in entries)
    
    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.name,
        "total_debt": total_debt,
        "pending_entries": len(entries)
    }
    
    
from datetime import datetime, date
from typing import Optional
from fastapi import Query
'''
@router.get("/entries/summary")
def get_purchase_entries_summary(
    start_date: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    supplier_id: Optional[int] = Query(None, description="Filtrar por proveedor"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse_user)
):
    """
    Obtiene un resumen de las entradas de productos en un período.
    """
    print(start_date)
    print(end_date)
    query = db.query(PurchaseEntry)
    
    # Filtros de fecha
    if start_date:
        query = query.filter(PurchaseEntry.entry_date >= start_date)
    if end_date:
        query = query.filter(PurchaseEntry.entry_date <= end_date)
    if supplier_id:
        query = query.filter(PurchaseEntry.supplier_id == supplier_id)
    
    # Obtener todas las entradas del período
    entries = query.all()
    
    # Calcular resumen
    total_entries = len(entries)
    total_amount = sum(e.total_amount for e in entries)
    total_paid = sum(e.paid_amount for e in entries)
    total_balance = total_amount - total_paid
    
    # Agrupar por proveedor
    suppliers_summary = {}
    for entry in entries:
        supplier_name = entry.supplier.name if entry.supplier else "Sin proveedor"
        if supplier_name not in suppliers_summary:
            suppliers_summary[supplier_name] = {
                "supplier_id": entry.supplier_id,
                "total_entries": 0,
                "total_amount": 0,
                "total_paid": 0,
                "balance": 0
            }
        suppliers_summary[supplier_name]["total_entries"] += 1
        suppliers_summary[supplier_name]["total_amount"] += entry.total_amount
        suppliers_summary[supplier_name]["total_paid"] += entry.paid_amount
        suppliers_summary[supplier_name]["balance"] = (
            suppliers_summary[supplier_name]["total_amount"] - 
            suppliers_summary[supplier_name]["total_paid"]
        )
    
    # Detalle de productos más comprados
    product_summary = {}
    for entry in entries:
        for item in entry.items:
            product_name = item.product.name if item.product else f"Producto {item.product_id}"
            if product_name not in product_summary:
                product_summary[product_name] = {
                    "product_id": item.product_id,
                    "total_quantity": 0,
                    "total_spent": 0
                }
            product_summary[product_name]["total_quantity"] += item.quantity
            product_summary[product_name]["total_spent"] += item.subtotal
    
    # Ordenar productos por cantidad comprada (top 5)
    top_products = sorted(
        product_summary.items(),
        key=lambda x: x[1]["total_quantity"],
        reverse=True
    )[:5]
    
    return {
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        },
        "summary": {
            "total_entries": total_entries,
            "total_amount": total_amount,
            "total_paid": total_paid,
            "total_balance": total_balance,
            "average_entry_value": total_amount / total_entries if total_entries > 0 else 0
        },
        "by_supplier": suppliers_summary,
        "top_products": [
            {
                "product_name": name,
                **data
            }
            for name, data in top_products
        ]
    }
'''
    