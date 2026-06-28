from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
from datetime import datetime, timedelta

from database.database import get_db
from models.user_models import User, UserRole
from routers.auth import get_current_user, get_password_hash, verify_password, create_access_token
from models.inventory_models import Product, WarehouseStock, POSLocation, POSStock
from models.cash_models import Sale, SaleItem, CashRegister, CashWithdrawalRequest, WithdrawalStatus
from schemas.cash_schemas import SaleItemCreate

# Configuración de la app web
app = FastAPI(title="Sistema de Inventarios - Web")

# Configurar templates y archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Variable global para simular sesión (en producción usarías JWT en cookies)
user_sessions = {}

# Dependencia para obtener usuario actual en templates
async def get_current_user_web(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if token:
        try:
            from routers.auth import get_current_user
            user = await get_current_user(token=token, db=db)
            return user
        except:
            return None
    return None

# Middleware para inyectar usuario actual en templates
@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    response = await call_next(request)
    return response