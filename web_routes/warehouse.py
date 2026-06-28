from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from database.database import get_db
from web_app import templates, get_current_user_web
from models.user_models import User, UserRole
from models.inventory_models import Product, WarehouseStock

router = APIRouter()

@router.get("/warehouse/products", response_class=HTMLResponse)
async def products_list(
    request: Request,
    search: str = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        return RedirectResponse("/auth/login")
    
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        return RedirectResponse("/")
    
    # Consulta de productos con paginación
    query = db.query(Product)
    
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) | 
            (Product.sku.ilike(f"%{search}%"))
        )
    
    # Paginación
    page_size = 10
    offset = (page - 1) * page_size
    total_products = query.count()
    total_pages = (total_products + page_size - 1) // page_size
    
    products = query.offset(offset).limit(page_size).all()
    
    return templates.TemplateResponse(
        "warehouse/products.html",
        {
            "request": request,
            "current_user": current_user,
            "products": products,
            "search": search,
            "current_page": page,
            "total_pages": total_pages
        }
    )

@router.get("/warehouse/products/new", response_class=HTMLResponse)
async def new_product_form(
    request: Request,
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        return RedirectResponse("/auth/login")
    
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        return RedirectResponse("/")
    
    return templates.TemplateResponse(
        "warehouse/product_form.html",
        {
            "request": request,
            "current_user": current_user,
            "product": None
        }
    )

@router.post("/warehouse/products")
async def create_product(
    request: Request,
    name: str = Form(...),
    sku: str = Form(...),
    price: float = Form(...),
    cost: float = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        return RedirectResponse("/auth/login")
    
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        return RedirectResponse("/")
    
    # Verificar si el SKU ya existe
    existing_product = db.query(Product).filter(Product.sku == sku).first()
    if existing_product:
        return templates.TemplateResponse(
            "warehouse/product_form.html",
            {
                "request": request,
                "current_user": current_user,
                "error": "El SKU ya existe"
            }
        )
    
    # Crear nuevo producto
    product = Product(
        name=name,
        sku=sku,
        price=price,
        cost=cost,
        description=description
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Crear registro de stock
    warehouse_stock = WarehouseStock(
        product_id=product.id,
        quantity=0
    )
    db.add(warehouse_stock)
    db.commit()
    
    return RedirectResponse("/warehouse/products", status_code=302)