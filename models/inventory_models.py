from sqlalchemy import Column, Integer, String, Float, Boolean,ForeignKey, DateTime, Text, Enum as SQLEnum
#from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base


from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum



class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relación con Product (uno a muchos)
    products = relationship("Product", back_populates="category")







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
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)   # ⭐ nueva FK
    has_inventory = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # COMENTAR relaciones por ahora
    warehouse_stock = relationship("WarehouseStock", back_populates="product", uselist=False)
    transfers = relationship("TransferToPOS", back_populates="product")
    category = relationship("Category", back_populates="products")
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
    cashiers = relationship("User", back_populates="pos_location")
    #pos_stocks = relationship("POSStock", back_populates="pos_location")
    # sales = relationship("Sale", back_populates="pos_location")
    
    cash_registers = relationship("CashRegister", back_populates="pos_location")

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
    
    


# ---- Enums ----
class DocumentType(str, enum.Enum):
    INVOICE = "invoice"
    DELIVERY_NOTE = "delivery_note"
    RECEIPT = "receipt"

class PurchaseStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# ---- Proveedor ----
'''class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # Código interno
    contract_number = Column(String, unique=True, nullable=True)
    document_type = Column(SQLEnum(DocumentType), nullable=False, default=DocumentType.INVOICE)
    tax_id = Column(String, nullable=True)  # RUC / NIT
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    purchases = relationship("Purchase", back_populates="supplier")
'''
# ---- Compra (Purchase) ----
# models/inventory_models.py

# ... imports existentes ...
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, Enum as SQLEnum, Numeric, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
from schemas.enums import DocumentType, SupplierStatus, PurchaseOrderStatus

# ... tus tablas existentes (Product, Category, WarehouseStock, etc.) ...

# ========== SUPPLIER ==========
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False, index=True)
    contract_number = Column(String, nullable=True)
    document_type = Column(String, nullable=False)  # 'invoice', 'conduce', etc.
    contact_phone = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relaciones
    purchase_entries = relationship("PurchaseEntry", back_populates="supplier")

# ========== PURCHASE ENTRY ==========
class PurchaseEntry(Base):
    __tablename__ = "purchase_entries"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    entry_date = Column(DateTime, server_default=func.now())
    total_amount = Column(Float, nullable=False, default=0)
    paid_amount = Column(Float, nullable=False, default=0)
    status = Column(String, default="pending")  # pending, partial, paid, cancelled
    notes = Column(Text, nullable=True)

    # Relaciones
    supplier = relationship("Supplier", back_populates="purchase_entries")
    items = relationship("PurchaseItem", back_populates="purchase_entry", cascade="all, delete-orphan")

# ========== PURCHASE ITEM ==========
class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_entry_id = Column(Integer, ForeignKey("purchase_entries.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    discount = Column(Float, default=0)

    # Relaciones
    purchase_entry = relationship("PurchaseEntry", back_populates="items")
    product = relationship("Product")