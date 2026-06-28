from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database.database import get_db
from web_app import templates, get_current_user_web
from models.user_models import User
from models.inventory_models import Product, WarehouseStock, POSLocation
from models.cash_models import Sale, CashWithdrawalRequest, WithdrawalStatus, CashRegister

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        return RedirectResponse("/auth/login")
    
    # Estadísticas para el dashboard
    today = datetime.now().date()
    
    # Ventas de hoy
    today_sales = db.query(func.sum(Sale.total_amount)).filter(
        func.date(Sale.sale_date) == today
    ).scalar() or 0
    
    # Total de productos
    total_products = db.query(Product).count()
    
    # Puntos de venta
    total_pos_locations = db.query(POSLocation).count()
    
    # Retiros pendientes
    pending_withdrawals = db.query(CashWithdrawalRequest).filter(
        CashWithdrawalRequest.status == WithdrawalStatus.PENDING
    ).count()
    
    # Ventas recientes
    recent_sales = db.query(Sale).order_by(desc(Sale.sale_date)).limit(10).all()
    
    # Productos con stock bajo
    low_stock_items = db.query(WarehouseStock).join(Product).filter(
        WarehouseStock.quantity <= WarehouseStock.min_stock
    ).limit(5).all()
    
    stats = {
        "today_sales": today_sales,
        "total_products": total_products,
        "total_pos_locations": total_pos_locations,
        "pending_withdrawals": pending_withdrawals
    }
    
    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "recent_sales": recent_sales,
            "low_stock_items": low_stock_items
        }
    )

@router.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        return RedirectResponse("/auth/login")
    
    return templates.TemplateResponse(
        "dashboard/profile.html",
        {
            "request": request,
            "current_user": current_user
        }
    )