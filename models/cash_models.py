from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    pos_location_id = Column(Integer, ForeignKey("pos_locations.id"), nullable=False)
    cashier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Float, nullable=False)

    # Desglose de pagos (reemplaza cash_received)
    cash_amount = Column(Float, default=0.0, nullable=False)          # efectivo recibido
    transfer_amount = Column(Float, default=0.0, nullable=False)      # transferencia recibida
    change_given = Column(Float, default=0.0)                         # vuelto (antes change)

    # Tipo de venta
    sale_type = Column(String(20), default="individual", nullable=False)  # individual, batch

    # Notas (para cierre de caja, diferencias, etc.)
    notes = Column(Text, nullable=True)

    sale_date = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    pos_location = relationship("POSLocation", back_populates="sales")
    cashier = relationship("User", back_populates="sales")
    sale_items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    
class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    # COMENTAR relaciones
    sale = relationship("Sale", back_populates="sale_items")
    product = relationship("Product", back_populates="sale_items")

class CashRegister(Base):
    __tablename__ = "cash_registers"

    id = Column(Integer, primary_key=True, index=True)
    pos_location_id = Column(Integer, ForeignKey("pos_locations.id"), unique=True)
    current_balance = Column(Float, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # COMENTAR relaciones
    pos_location = relationship("POSLocation", back_populates="cash_registers")
    
    # withdrawals = relationship("CashWithdrawal", back_populates="cash_register")

class CashWithdrawal(Base):
    __tablename__ = "cash_withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    cash_register_id = Column(Integer, ForeignKey("cash_registers.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    withdrawal_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # COMENTAR relaciones
    # cash_register = relationship("CashRegister", back_populates="withdrawals")
    # user = relationship("User", back_populates="cash_withdrawals")

class CashWithdrawalRequest(Base):
    __tablename__ = "cash_withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    pos_location_id = Column(Integer, ForeignKey("pos_locations.id"))
    cashier_id = Column(Integer, ForeignKey("users.id"))
    authorizer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, default="pending")
    request_date = Column(DateTime(timezone=True), server_default=func.now())
    authorized_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # COMENTAR relaciones
    # pos_location = relationship("POSLocation")
    # cashier = relationship("User", foreign_keys=[cashier_id])
    # authorizer = relationship("User", foreign_keys=[authorizer_id])