from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import uvicorn
import os

from database.database import get_db, engine, Base

# Sistema de autenticación simple
from fastapi import HTTPException
current_user_session = None

async def get_current_user_web(request: Request, db: Session = Depends(get_db)):
    """Obtener usuario actual para la web"""
    global current_user_session
    
    # Para desarrollo, usar admin por defecto
    from models.user_models import User
    user = db.query(User).filter(User.username == "admin").first()
    
    if user:
        return user
    
    # Si no hay usuario, redirigir al login
    return None


# Crear tablas PRIMERO, antes de cualquier import de modelos
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Inventarios Web",
    description="Interfaz web del sistema de inventarios",
    version="1.0.0"
)

# Configurar archivos estáticos
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurar templates
templates = Jinja2Templates(directory="templates")

# ===== RUTAS PRINCIPALES =====

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return RedirectResponse("/auth/login")

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "auth/login.html", 
        {
            "request": request, 
            "error": None
        }
    )

@app.post("/auth/login")
async def web_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Procesar login web"""
    try:
        from routers.auth import authenticate_user
        from web_auth import set_current_user
        
        print(f"🔐 Intentando login para: {username}")
        
        # Autenticar usuario
        user = authenticate_user(db, username, password)
        
        if not user:
            print("❌ Autenticación fallida")
            return templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "error": "Usuario o contraseña incorrectos",
                    "username": username
                }
            )
        
        print(f"✅ Login exitoso para: {user.full_name} ({user.role})")
        
        # Establecer sesión
        set_current_user(user.username)
        
        # Redirigir al dashboard
        response = RedirectResponse("/dashboard", status_code=302)
        return response
        
    except Exception as e:
        print(f"❌ Error en login: {str(e)}")
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": f"Error del sistema: {str(e)}"
            }
        )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard principal"""
    try:
        from models.inventory_models import Product, POSLocation, WarehouseStock
        from models.cash_models import Sale, CashWithdrawalRequest
        from sqlalchemy import func, desc
        from datetime import datetime
        
        print("📊 Cargando dashboard...")
        
        # Estadísticas básicas
        today = datetime.now().date()
        
        # Ventas de hoy
        today_sales = db.query(func.sum(Sale.total_amount)).filter(
            func.date(Sale.sale_date) == today
        ).scalar() or 0
        
        # Total productos
        total_products = db.query(Product).count()
        
        # Puntos de venta
        total_pos_locations = db.query(POSLocation).count()
        
        # Retiros pendientes
        pending_withdrawals = db.query(CashWithdrawalRequest).filter(
            CashWithdrawalRequest.status == "pending"
        ).count()
        
        # Ventas recientes (últimas 5)
        recent_sales = db.query(Sale).order_by(desc(Sale.sale_date)).limit(5).all()
        
        # Stock bajo
        low_stock_items = db.query(WarehouseStock).join(Product).filter(
            WarehouseStock.quantity <= WarehouseStock.min_stock
        ).limit(5).all()
        
        stats = {
            "today_sales": today_sales,
            "total_products": total_products,
            "total_pos_locations": total_pos_locations,
            "pending_withdrawals": pending_withdrawals
        }
        
        # Usuario simulado para desarrollo
        current_user = {"full_name": "Administrador", "role": "admin"}
        
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
        
    except Exception as e:
        print(f"❌ Error en dashboard: {str(e)}")
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error cargando dashboard</h1>
            <p>{str(e)}</p>
            <a href="/auth/login">Volver al login</a>
        </body>
        </html>
        """
        return HTMLResponse(error_html)
'''@app.get("/dashboard/simple", response_class=HTMLResponse)
async def dashboard_simple(request: Request):
    """Dashboard simple sin base de datos"""
    try:
        current_user = {"full_name": "Administrador", "role": "admin"}
        stats = {
            "today_sales": 1250.50,
            "total_products": 15,
            "total_pos_locations": 3,
            "pending_withdrawals": 2
        }
        
        return templates.TemplateResponse(
            "dashboard/index.html",
            {
                "request": request,
                "current_user": current_user,
                "stats": stats,
                "recent_sales": [],
                "low_stock_items": []
            }
        )
    except Exception as e:
        return HTMLResponse(f"<h1>Error: {str(e)}</h1>")'''
    
if __name__ == "__main__":
    print("🚀 Servidor Web Iniciado: http://localhost:8000")
    uvicorn.run("main_web:app", host="0.0.0.0", port=8000, reload=True)