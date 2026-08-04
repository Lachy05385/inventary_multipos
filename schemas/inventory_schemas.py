from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import datetime
from .enums import DocumentType, PurchaseEntryStatus

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

# ---- Product Schemas ----
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku: str
    price: float
    cost: Optional[float] = None
    image_url: Optional[str] = None
    min_stock: int = 0
    category_id: Optional[int] = None
    has_inventory: bool = True

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
    has_inventory: Optional[bool] = None

class Product(ProductBase):
    id: int
    created_at: datetime
    category: Optional[Category] = None

    class Config:
        from_attributes = True

# ---- Warehouse Stock Schemas ----
class WarehouseStockBase(BaseModel):
    product_id: int
    quantity: int
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

# ---- Warehouse Entry (para ajustes manuales de stock) ----
class WarehouseEntryBase(BaseModel):
    product_id: int
    quantity: int
    supplier_id: Optional[int] = None
    purchase_entry_id: Optional[int] = None
    notes: Optional[str] = None

class WarehouseEntryCreate(WarehouseEntryBase):
    pass

class WarehouseEntry(WarehouseEntryBase):
    id: int
    entry_date: datetime
    status: str
    cancelled_by: Optional[int]
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]

    class Config:
        from_attributes = True

class WarehouseEntryWithDetails(WarehouseEntry):
    product: Product
    supplier: Optional["Supplier"]  # usar string para evitar forward reference
    canceller: Optional["User"]     # usar string

    class Config:
        from_attributes = True

# ---- POS Location Schemas ----
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

# ---- POS Stock Schemas ----
class POSStockBase(BaseModel):
    product_id: int
    pos_location_id: int
    quantity: int

class POSStockCreate(POSStockBase):
    pass

class POSStockUpdate(BaseModel):
    quantity: Optional[int] = None

class POSStock(POSStockBase):
    id: int
    last_updated: datetime

    class Config:
        from_attributes = True

class POSStockWithProduct(POSStock):
    product: Product
    pos_location: POSLocation

    class Config:
        from_attributes = True

# ---- Transfer Schemas ----
class TransferBase(BaseModel):
    product_id: int
    pos_location_id: int
    quantity: int

class TransferCreate(TransferBase):
    pass

class TransferUpdate(BaseModel):
    quantity: Optional[int] = None
    status: Optional[str] = None

class Transfer(TransferBase):
    id: int
    warehouse_stock_id: int
    transferred_by: int
    transfer_date: datetime
    status: str

    class Config:
        from_attributes = True

class TransferWithDetails(Transfer):
    product: Product
    pos_location: POSLocation

    class Config:
        from_attributes = True

# ---- Supplier Schemas ----
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

# ---- Purchase Item Schemas ----
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

    class Config:
        from_attributes = True

class PurchaseItemWithProduct(PurchaseItem):
    product: Product

    class Config:
        from_attributes = True

# ---- Purchase Entry Schemas ----
class PurchaseEntryBase(BaseModel):
    supplier_id: int
    notes: Optional[str] = None

class PurchaseEntryCreate(PurchaseEntryBase):
    items: List[PurchaseItemCreate]
    document_number: Optional[str] = None
    document_date: Optional[datetime] = None
    paid_amount: float = 0

class PurchaseEntryUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[PurchaseEntryStatus] = None
    paid_amount: Optional[float] = None

class PurchaseEntry(PurchaseEntryBase):
    id: int
    entry_date: datetime
    total_amount: float
    paid_amount: float
    status: PurchaseEntryStatus
    document_number: Optional[str]
    document_date: Optional[datetime]

    class Config:
        from_attributes = True

class PurchaseEntryWithDetails(PurchaseEntry):
    supplier: Supplier
    items: List[PurchaseItemWithProduct]

    @computed_field
    @property
    def balance(self) -> float:
        return self.total_amount - self.paid_amount

    class Config:
        from_attributes = True