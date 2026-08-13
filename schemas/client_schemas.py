# schemas/client_schemas.py
from pydantic import BaseModel, EmailStr, validator,Field
from typing import Optional, List
from datetime import datetime
from models.inventory_models import Product


# ========== DIRECCIÓN DE ENTREGA ==========
class DeliveryAddressBase(BaseModel):
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "Cuba"
    is_default: bool = False

class DeliveryAddressCreate(DeliveryAddressBase):
    pass

class DeliveryAddress(DeliveryAddressBase):
    id: int
    client_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ========== CLIENTE ==========
class ClientBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None

class ClientCreate(ClientBase):
    password: str
    address: Optional[DeliveryAddressCreate] = None  # Dirección opcional al registrarse

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        return v

class ClientUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

class Client(ClientBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    addresses: List[DeliveryAddress] = []

    class Config:
        from_attributes = True

# ========== AUTENTICACIÓN DE CLIENTE ==========
class ClientLogin(BaseModel):
    email: EmailStr
    password: str

class ClientToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    client: Client  # Devuelve datos del cliente junto con el token
    
    class Config:
        from_attributes = True  # ⬅️ Permite convertir desde SQLAlchemy
        
        
        
# CARRITO DE COMPRAS SCHEMAS 


class CartItemBase(BaseModel):
    product_id: int
    quantity: int

class CartItemCreate(CartItemBase):
    pass

class CartItem(CartItemBase):
    id: int
    cart_id: int
    product: Product  # o un sub-esquema con nombre, precio, etc.

class Cart(BaseModel):
    id: int
    client_id: int
    items: List[CartItem]
    total: float  # calculado