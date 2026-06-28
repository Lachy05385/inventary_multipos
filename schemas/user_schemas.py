from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from enum import Enum
from datetime import datetime

class UserRole(str, Enum):
    ADMIN = "admin"
    WAREHOUSE_MANAGER = "warehouse_manager"
    CASHIER = "cashier"

class UserBase(BaseModel):
    email: str  # Cambiado de EmailStr a str temporalmente
    username: str
    full_name: str
    role: UserRole
    pos_location_id: Optional[int] = None

    @validator('email')
    def validate_email(cls, v):
        # Validación básica de email
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    pos_location_id: Optional[int] = None
    is_active: Optional[bool] = None

    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str