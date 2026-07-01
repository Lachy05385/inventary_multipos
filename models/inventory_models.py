from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    sku = Column(String, unique=True, index=True)
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # COMENTAR relaciones por ahora
    warehouse_stock = relationship("WarehouseStock", back_populates="product", uselist=False)
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
    warehouse_stock_id = Column(Integer, ForeignKey("warehouse_stocks.id"))
    pos_location_id = Column(Integer, ForeignKey("pos_locations.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    transfer_date = Column(DateTime(timezone=True), server_default=func.now())
    transferred_by = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="completed")
    
    # COMENTAR relaciones
    # warehouse_stock = relationship("WarehouseStock", back_populates="transfers_to_pos")
    # pos_location = relationship("POSLocation")
    # product = relationship("Product")