# schemas/enums.py
from enum import Enum

class DocumentType(str, Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    DELIVERY_NOTE = "delivery_note"
    PURCHASE_ORDER = "purchase_order"
    CONTRACT = "contract"
    OTHER = "other"

class SupplierStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class PurchaseOrderStatus(str, Enum):
    PENDING = "pending"
    RECEIVED = "received"
    CANCELLED = "cancelled"
    PARTIAL = "partial"
    
class PurchaseEntryStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    CANCELLED = "cancelled"
