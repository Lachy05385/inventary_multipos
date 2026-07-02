from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    sku = Column(String, unique=True, nullable=False, index=True)
    price = Column(Float, nullable=False)
    cost = Column(Float)
    image_url = Column(String, nullable=True)          # URL de la imagen
    min_stock = Column(Integer, default=0)             # ⭐ stock mínimo (alertas)
    created_at = Column(DateTime, server_default=func.now())
    # COMENTAR relaciones por ahora
    warehouse_stock = relationship("WarehouseStock", back_populates="product", uselist=False)
    transfers = relationship("TransferToPOS", back_populates="product")
    # warehouse_stock = relationship("WarehouseStock", back_populates="product", uselist=False)
    # pos_stocks = relationship("POSStock", back_populates="product")
    # sale_items = relationship("SaleItem", back_populates="product")



class WarehouseStock(Base):
    __tablename__ = "warehouse_stock"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)
    quantity = Column(Integer, default=0, nullable=False)
    min_stock = Column(Integer, default=10, nullable=False)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ⭐ Relación con Product – nómbrala 'product' (coincide con el esquema)
    
    product = relationship("Product", back_populates="warehouse_stock")# transfers_to_pos = relationship("TransferToPOS", back_populates="warehouse_stock")
    transfers = relationship("TransferToPOS", back_populates="warehouse_stock")
#=============================================
'''class WarehouseStock(Base):
    __tablename__ = "warehouse_stock"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)  # un producto solo tiene un registro en almacén
    quantity = Column(Integer, default=0, nullable=False)
    min_stock = Column(Integer, default=0, nullable=False)   # stock mínimo para alertas
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

# Relación con Product (usamos el nombre 'product_rel' para que coincida con tu código)
product_rel = relationship("Product", back_populates="warehouse_stock")  # si tienes la relación inversa
'''

#=============================================
class POSLocation(Base):
    __tablename__ = "pos_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # COMENTAR relaciones
    # cashiers = relationship("User", back_populates="pos_location")
    # pos_stocks = relationship("POSStock", back_populates="pos_location")
    # sales = relationship("Sale", back_populates="pos_location")
    # cash_registers = relationship("CashRegister", back_populates="pos_location")

class POSStock(Base):
    __tablename__ = "pos_stocks"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    pos_location_id = Column(Integer, ForeignKey("pos_locations.id"))
    quantity = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # COMENTAR relaciones
    # product = relationship("Product", back_populates="pos_stocks")
    # pos_location = relationship("POSLocation", back_populates="pos_stocks")

class TransferToPOS(Base):
    __tablename__ = "transfers_to_pos"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    pos_location_id = Column(Integer, ForeignKey("pos_locations.id"), nullable=False)
    warehouse_stock_id = Column(Integer, ForeignKey("warehouse_stock.id"), nullable=False)  # ⭐ clave foránea
    quantity = Column(Integer, nullable=False)
    transferred_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    transfer_date = Column(DateTime, server_default=func.now())
    status = Column(String, default="pending")  # pending, completed, cancelled
    
    # COMENTAR relaciones
    product = relationship("Product")
    pos_location = relationship("POSLocation")
    warehouse_stock = relationship("WarehouseStock", back_populates="transfers")  # relación inversa
    user = relationship("User", foreign_keys=[transferred_by])  # quien transfirió