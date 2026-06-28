from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from database.database import Base

class UserRole(str, Enum):
    ADMIN = "admin"
    WAREHOUSE_MANAGER = "warehouse_manager"
    CASHIER = "cashier"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(SQLEnum(UserRole), default=UserRole.CASHIER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relación con puntos de venta (solo la FK, sin relationship por ahora)
    pos_location_id = Column(Integer, ForeignKey("pos_locations.id"), nullable=True)
    
    # COMENTAR las relaciones por ahora para evitar problemas circulares
    # pos_location = relationship("POSLocation", back_populates="cashiers")
    # sales = relationship("Sale", back_populates="cashier")
    # cash_withdrawals = relationship("CashWithdrawal", back_populates="user")