from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

# Sale Item Schemas
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

# Sale Schemas
class SaleBase(BaseModel):
    pos_location_id: int
    cash_received: float

class SaleCreate(BaseModel):
    items: List[SaleItemCreate]
    cash_received: float

class SaleUpdate(BaseModel):
    cash_received: Optional[float] = None

class Sale(SaleBase):
    id: int
    cashier_id: int
    total_amount: float
    change: float
    sale_date: datetime

    class Config:
        from_attributes = True

class SaleWithDetails(Sale):
    sale_items: List[SaleItemWithProduct]
    cashier_name: str
    pos_location_name: str

    class Config:
        from_attributes = True

# Cash Register Schemas
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
    pos_location: str

    class Config:
        from_attributes = True

# Cash Withdrawal Schemas
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

# Dashboard/Report Schemas
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
    alert_type: str  # "low_stock", "out_of_stock"
    
#schemas para retiros 
class WithdrawalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

# Schemas para Solicitudes de Retiro
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

# Schema para completar retiro
class CompleteWithdrawalRequest(BaseModel):
    withdrawal_request_id: int