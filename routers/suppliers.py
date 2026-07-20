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