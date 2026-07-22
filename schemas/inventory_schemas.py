from pydantic import BaseModel, computed_field
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
    price: float
    cost: Optional[float] = None
    image_url: Optional[str] = None
    min_stock: int = 0
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
    quantity: int

class POSStockCreate(POSStockBase):
    pass

class POSStockUpdate(BaseModel):
    quantity: Optional[int] = None

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
    class Config:
        from_attributes = True

class PurchaseItemWithProduct(PurchaseItem):
    product: Product

# ========== PURCHASE ENTRY SCHEMAS ==========
class PurchaseEntryBase(BaseModel):
    supplier_id: int
    notes: Optional[str] = None

class PurchaseEntryCreate(PurchaseEntryBase):
    items: List[PurchaseItemCreate]

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
    class Config:
        from_attributes = True

class PurchaseEntryWithDetails(PurchaseEntry):
    supplier: Supplier
    items: List[PurchaseItemWithProduct]
    #balance: float  # total_amount - paid_amount
    
    @computed_field
    @property
    def balance(self) -> float:
        return self.total_amount - self.paid_amount