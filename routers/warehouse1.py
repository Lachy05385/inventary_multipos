from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from models.user_models import User, UserRole
from models.inventory_models import Product, WarehouseStock, POSLocation, TransferToPOS, POSStock
from schemas.inventory_schemas import (
    ProductCreate, Product as ProductSchema, 
    WarehouseStock as WarehouseStockSchema,
    TransferCreate, Transfer as TransferSchema
)
from routers.auth import get_current_user

router = APIRouter