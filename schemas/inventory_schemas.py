from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Product Schemas
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku: str
    price: float
    cost: Optional[float] = None
    image_url: Optional[str] = None          # nuevo
    min_stock: int = 0                       # nuevo

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

class Product(ProductBase):
    id: int
    created_at: datetime
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