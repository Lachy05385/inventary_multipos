

# ---- Payment Schemas ----
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
from schemas.inventory_schemas import POSLocation

# ========== ENUM PARA MÉTODOS DE PAGO ==========
class PaymentMethod(str, Enum):
    CASH = "cash"
    TRANSFER = "transfer"

# ========== DETALLE DE PAGO ==========
class PaymentDetail(BaseModel):
    method: PaymentMethod
    amount: float

# ========== SALE ITEM SCHEMAS ==========
class SaleItemBase(BaseModel):
    product_id: int
    quantity: int

class SaleItemCreate(SaleItemBase):
    pass

class SaleItem(SaleItemBase):
    id: int
    sale_id: int
    unit_price: float
    subtotal: float
    class Config:
        from_attributes = True

class SaleItemWithProduct(SaleItem):
    product_name: str
    class Config:
        from_attributes = True

# ========== SALE SCHEMAS ==========
class SaleBase(BaseModel):
    pos_location_id: int

class SaleCreate(BaseModel):
    items: List[SaleItemCreate]
    payments: List[PaymentDetail]  # ⬅️ Lista de pagos (ej: [{"method": "cash", "amount": 50.0}, {"method": "transfer", "amount": 30.0}])

class SaleUpdate(BaseModel):
    # No permitimos actualizar ventas directamente, solo cancelar
    pass

class Sale(SaleBase):
    id: int
    cashier_id: int
    total_amount: float
    payment_details: Dict[str, float]  # ⬅️ Diccionario: {"cash": 50.0, "transfer": 30.0}
    change: float
    sale_date: datetime
    status: str = "completed"
    cancelled_by: Optional[int] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    
    
    
    
    class Config:
        from_attributes = True

class SaleWithDetails(Sale):
    sale_items: List[SaleItemWithProduct]
    cashier_name: str
    pos_location_name: str
    canceller_name: Optional[str] = None
    class Config:
        from_attributes = True

# ---- Cash Register Schemas ----
class CashRegisterBase(BaseModel):
    pos_location_id: int
    current_balance: float

class CashRegisterCreate(CashRegisterBase):
    pass

class CashRegisterUpdate(BaseModel):
    current_balance: Optional[float] = None

class CashRegister(CashRegisterBase):
    id: int
    last_updated: datetime

    class Config:
        from_attributes = True

class CashRegisterWithLocation(CashRegister):
    pos_location: POSLocation

    class Config:
        from_attributes = True

# ---- Cash Withdrawal Schemas ----
class CashWithdrawalBase(BaseModel):
    pos_location_id: int
    amount: float
    reason: Optional[str] = None

class CashWithdrawalCreate(CashWithdrawalBase):
    pass

class CashWithdrawalUpdate(BaseModel):
    amount: Optional[float] = None
    reason: Optional[str] = None

class CashWithdrawal(CashWithdrawalBase):
    id: int
    cash_register_id: int
    user_id: int
    withdrawal_date: datetime

    class Config:
        from_attributes = True

class CashWithdrawalWithDetails(CashWithdrawal):
    user_name: str
    pos_location_name: str

    class Config:
        from_attributes = True

# ---- Dashboard/Report Schemas ----
class SalesReport(BaseModel):
    total_sales: float
    total_transactions: int
    average_sale: float
    date_range: str

class CashFlowReport(BaseModel):
    total_income: float
    total_withdrawals: float
    net_cash_flow: float
    current_balances: List[CashRegisterWithLocation]

class InventoryAlert(BaseModel):
    product_id: int
    product_name: str
    current_stock: int
    min_stock: int
    alert_type: str

# ---- Cash Withdrawal Request Schemas ----
class WithdrawalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class CashWithdrawalRequestBase(BaseModel):
    pos_location_id: int
    amount: float
    reason: str

class CashWithdrawalRequestCreate(CashWithdrawalRequestBase):
    pass

class CashWithdrawalRequestUpdate(BaseModel):
    status: Optional[WithdrawalStatus] = None
    rejection_reason: Optional[str] = None

class CashWithdrawalRequestAuthorize(BaseModel):
    authorizer_id: int
    status: WithdrawalStatus

class CashWithdrawalRequest(CashWithdrawalRequestBase):
    id: int
    cashier_id: int
    authorizer_id: Optional[int]
    status: WithdrawalStatus
    request_date: datetime
    authorized_date: Optional[datetime]
    completed_date: Optional[datetime]
    rejection_reason: Optional[str]

    class Config:
        from_attributes = True

class CashWithdrawalRequestWithDetails(CashWithdrawalRequest):
    cashier_name: str
    authorizer_name: Optional[str]
    pos_location_name: str

    class Config:
        from_attributes = True

class CompleteWithdrawalRequest(BaseModel):
    withdrawal_request_id: int