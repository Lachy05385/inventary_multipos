from pydantic import BaseModel, computed_field,Field
from decimal import Decimal
from typing import Optional,List
from datetime import datetime
from models.inventory_models import Supplier
from .enums import DocumentType, PurchaseOrderStatus

# ---- Category Schemas ----
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Category(CategoryBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True







# Product Schemas
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku: str
    price: Decimal
    cost: Optional[Decimal] = None
    image_url: Optional[str] = None
    min_stock: Decimal = 0
    category_id: Optional[int] = None   # ⭐ nuevo
    has_inventory: bool = True   # ⭐ NUEVO (por defecto True)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    image_url: Optional[str] = None
    min_stock: Optional[int] = None
    category_id: Optional[int] = None
    has_inventory: Optional[bool] = None   # ⭐ NUEVO


class Product(ProductBase):
    id: int
    created_at: datetime
    category: Optional[Category] = None   # para incluir datos de la categoría en la respuesta
    class Config:
        from_attributes = True

# Warehouse Stock Schemas
class WarehouseStockBase(BaseModel):
    product_id: int
    quantity: Decimal
    min_stock: int = 10

class WarehouseStockCreate(WarehouseStockBase):
    pass

class WarehouseStockUpdate(BaseModel):
    quantity: Optional[int] = None
    min_stock: Optional[int] = None

class WarehouseStock(WarehouseStockBase):
    id: int
    last_updated: datetime

    class Config:
        from_attributes = True

class WarehouseStockWithProduct(WarehouseStock):
    product: Product

    class Config:
        from_attributes = True

# POS Location Schemas
class POSLocationBase(BaseModel):
    name: str
    address: str

class POSLocationCreate(POSLocationBase):
    pass

class POSLocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

class POSLocation(POSLocationBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# POS Stock Schemas
class POSStockBase(BaseModel):
    product_id: int
    pos_location_id: int
    quantity: Decimal

class POSStockCreate(POSStockBase):
    pass

class POSStockUpdate(BaseModel):
    quantity: Optional[Decimal] = None

class POSStock(POSStockBase):
    id: int
    #product_id: int #Agrege esto yo 
    last_updated: datetime

    class Config:
        from_attributes = True

class POSStockWithProduct(POSStock):
    
    product: Product
    pos_location: POSLocation

    class Config:
        from_attributes = True

# Transfer Schemas
class TransferBase(BaseModel):
    product_id: int
    pos_location_id: int
    quantity: Decimal

class TransferCreate(TransferBase):
    pass

class TransferUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    status: Optional[str] = None

class Transfer(TransferBase):
    id: int
    warehouse_stock_id: Decimal
    transferred_by: int
    transfer_date: datetime
    status: str
    
    
class TransferReceiveItem(BaseModel):
    item_id: int
    received_quantity: Decimal = Field(..., ge=0)


class TransferReceive(BaseModel):
    items: Optional[List[TransferReceiveItem]] = None
    notes: Optional[str] = None


class TransferWithDetails(Transfer):
    product: Product
    pos_location: POSLocation

class TransferItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: Decimal
    received_quantity: Optional[Decimal] = None
    product: Product  # asumiendo que ya tienes el schema Product importado

    

class TransferResponse(BaseModel):
    # Identificación
    id: int
    transfer_number: str

    # Destino
    pos_location_id: int
    pos_location: POSLocation

    # Auditoría de envío
    sent_by_id: int
    sent_by_name: Optional[str] = None
    sent_at: datetime

    # Auditoría de recepción
    received_by_id: Optional[int] = None
    received_by_name: Optional[str] = None
    received_at: Optional[datetime] = None

    # Auditoría de cancelación
    cancelled_by_id: Optional[int] = None
    cancelled_by_name: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None

    # Estado y datos
    status: str  # pending, received, cancelled
    notes: Optional[str] = None

    # Resumen
    total_items: int
    total_units: int

    # Líneas
    items: List[TransferItemResponse]





    class Config:
        from_attributes = True





# ---- Supplier Schemas ----
# schemas/inventory_schemas.py

# schemas/inventory_schemas.py
from .enums import DocumentType, PurchaseEntryStatus
# ... (ya tienes los imports de BaseModel, etc.)

# ========== SUPPLIER SCHEMAS ==========
class SupplierBase(BaseModel):
    name: str
    code: str
    contract_number: Optional[str] = None
    document_type: DocumentType = DocumentType.INVOICE
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    contract_number: Optional[str] = None
    document_type: Optional[DocumentType] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None

class Supplier(SupplierBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# ========== PURCHASE ITEM SCHEMAS ==========
class PurchaseItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    discount: float = 0

class PurchaseItemCreate(PurchaseItemBase):
    pass

class PurchaseItemUpdate(BaseModel):
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    discount: Optional[float] = None

class PurchaseItem(PurchaseItemBase):
    id: int
    purchase_entry_id: int
    subtotal: float
    

class PurchaseItemWithProduct(PurchaseItem):
    product: Product

    class Config:
        from_attributes = True
# ========== PURCHASE ENTRY SCHEMAS ==========
class PurchaseEntryBase(BaseModel):
    supplier_id: int
    notes: Optional[str] = None

class PurchaseEntryCreate(PurchaseEntryBase):
    items: List[PurchaseItemCreate]
    document_number: Optional[str] = None #faltaba
    document_date: Optional[datetime] = None
    paid_amount: Optional[float] = None  # para registrar pagos
class PurchaseEntryUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[PurchaseEntryStatus] = None
    paid_amount: Optional[float] = None  # para registrar pagos

class PurchaseEntry(PurchaseEntryBase):
    id: int
    entry_date: datetime
    total_amount: float
    paid_amount: float
    status: PurchaseEntryStatus
    

class PurchaseEntryWithDetails(PurchaseEntry):
    supplier: Supplier
    items: List[PurchaseItemWithProduct]
    #balance: float  # total_amount - paid_amount

    @computed_field
    @property
    def balance(self) -> float:
        return self.total_amount - self.paid_amount


# entrada de productos 
class PurchaseEntryCreateWithItems(BaseModel):
    supplier_id: int
    document_number: Optional[str] = None
    document_date: Optional[datetime] = None
    items: List[PurchaseItemCreate]
    notes: Optional[str] = None
    paid_amount: float = 0  # opcional, para pago al contado    
    
    class Config:
            from_attributes = True