from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

from schemas.inventory_schemas import POSLocation


# ==================== SALE ITEM ====================

class SaleItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class SaleItemCreate(SaleItemBase):
    pass


class SaleItemResponse(BaseModel):
    """Item de venta con detalles del producto."""
    id: Optional[int]=None
    product_id: int
    quantity: int
    unit_price: float
    subtotal: float
    product_name: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== SALE ====================

class SaleCreate(BaseModel):
    """Payload para registrar una venta individual."""
    items: List[SaleItemCreate] = Field(..., min_length=1)
    cash_amount: float = Field(0.0, ge=0, description="Monto pagado en efectivo")
    transfer_amount: float = Field(0.0, ge=0, description="Monto pagado por transferencia")
    notes: Optional[str] = None

    

class SaleResponse(BaseModel):
    """Respuesta de una venta individual o cierre por lote."""
    id: int
    pos_location_id: int
    cashier_id: int
    total_amount: float
    cash_amount: float
    transfer_amount: float
    change_given: float
    sale_type: str  # "individual" | "batch"
    notes: Optional[str] = None
    sale_date: datetime
    items: List[SaleItemResponse] = []
    cashier_name: Optional[str] = None
    pos_location_name: Optional[str] = None

    class Config:
        from_attributes = True


# Compatibilidad con endpoints antiguos (opcional)
SaleWithDetails = SaleResponse


# ==================== BATCH SALE (cierre por lote) ====================

class BatchSaleClose(BaseModel):
    """Cierre de caja del día con montos declarados manualmente."""
    cash_amount: float = Field(..., ge=0)
    transfer_amount: float = Field(..., ge=0)
    notes: Optional[str] = None


class BatchSaleResponse(BaseModel):
    id: int
    pos_location_id: int
    total_amount: float
    cash_amount: float
    transfer_amount: float
    sale_type: str
    sale_date: datetime
    total_individual_sales: float
    difference: float
    message: str

    class Config:
        from_attributes = True


# ==================== CASH REGISTER ====================

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


# ==================== CASH WITHDRAWAL (retiros) ====================

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


# ==================== WITHDRAWAL REQUESTS (solicitudes de retiro) ====================

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


# ==================== REPORTS / DASHBOARD ====================

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
    alert_type: str  # "low_stock" | "out_of_stock"