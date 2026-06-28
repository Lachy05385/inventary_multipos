from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from database.database import get_db
from web_app import templates, get_current_user_web
from models.user_models import User, UserRole
from models.inventory_models import POSLocation, POSStock, Product
from models.cash_models import Sale, SaleItem, CashRegister

router = APIRouter()

@router.get("/pos/sales", response_class=HTMLResponse)
async def sales_list(
    request: Request,
    start_date: str = Query(None),
    end_date: str = Query(None),
    pos_location_id: int = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        return RedirectResponse("/auth/login")
    
    # Consulta de ventas
    query = db.query(Sale)
    
    # Filtrar por fecha
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(Sale.sale_date >= start)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        query = query.filter(Sale.sale_date < end)
    
    # Filtrar por punto de venta
    if pos_location_id:
        query = query.filter(Sale.pos_location_id == pos_location_id)
    elif current_user.role == UserRole.CASHIER:
        # Cajeros solo ven sus ventas en su POS
        query = query.filter(Sale.pos_location_id == current_user.pos_location_id)
    
    # Estadísticas
    today = datetime.now().date()
    today_sales = db.query(func.sum(Sale.total_amount)).filter(
        func.date(Sale.sale_date) == today
    ).scalar() or 0
    
    month_start = today.replace(day=1)
    month_sales = db.query(func.sum(Sale.total_amount)).filter(
        Sale.sale_date >= month_start
    ).scalar() or 0
    
    total_sales_count = query.count()
    average_sale = db.query(func.avg(Sale.total_amount)).scalar() or 0
    
    # Paginación
    page_size = 10
    offset = (page - 1) * page_size
    total_sales = query.count()
    total_pages = (total_sales + page_size - 1) // page_size
    
    sales = query.order_by(desc(Sale.sale_date)).offset(offset).limit(page_size).all()
    pos_locations = db.query(POSLocation).all()
    
    stats = {
        "today_sales": today_sales,
        "month_sales": month_sales,
        "total_sales": total_sales_count,
        "average_sale": average_sale
    }
    
    return templates.TemplateResponse(
        "pos/sales.html",
        {
            "request": request,
            "current_user": current_user,
            "sales": sales,
            "pos_locations": pos_locations,
            "stats": stats,
            "start_date": start_date,
            "end_date": end_date,
            "selected_pos": pos_location_id,
            "current_page": page,
            "total_pages": total_pages
        }
    )

@router.get("/pos/sales/new", response_class=HTMLResponse)
async def new_sale_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        return RedirectResponse("/auth/login")
    
    # Obtener productos disponibles en el POS del cajero
    if current_user.role == UserRole.CASHIER:
        pos_stock = db.query(POSStock).filter(
            POSStock.pos_location_id == current_user.pos_location_id,
            POSStock.quantity > 0
        ).all()
    else:
        # Admin y gerentes pueden ver todos los productos
        pos_stock = db.query(POSStock).filter(POSStock.quantity > 0).all()
    
    return templates.TemplateResponse(
        "pos/sale_form.html",
        {
            "request": request,
            "current_user": current_user,
            "pos_stock": pos_stock
        }
    )