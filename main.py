# ============================
# IMPORTS (siempre al inicio)
# ============================
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from routers import clients
import uvicorn
from email_config import ConnectionConfig
# Importar modelos y base de datos
from database.database import engine, Base, get_db
import models
from models.user_models import Base as UserBase
from models.inventory_models import Base as InventoryBase
from models.cash_models import Base as CashBase
from models.relationships1 import *  # Relaciones entre modelos

# Importar routers
from routers import auth, users, categories, warehouse, pos, cash, suppliers

# ============================
# CREAR TABLAS EN LA BD
# ============================
Base.metadata.create_all(bind=engine)

# ============================
# INICIALIZAR FASTAPI
# ============================
app = FastAPI(
    title="Sistema de Inventarios Multi-POS",
    description="""Sistema completo de gestión de inventarios para negocios con múltiples puntos de venta.
    
    Características:
    - 🔐 Autenticación JWT con roles
    - 🏭 Gestión de Almacén Central
    - 🏪 Puntos de Venta Múltiples
    - 📦 Control de Inventario en tiempo real
    - 💰 Gestión de Efectivo y cajas
    - 📊 Reportes y Dashboard
    """,
    version="1.0.0",
    contact={"name": "Soporte Técnico", "email": "soporte@inventarios.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

# ============================
# MIDDLEWARES Y CORS
# ============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],  # Cambia por tu dominio en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logging de peticiones
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds() * 1000
    print(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms")
    return response

# ============================
# RUTAS Y ARCHIVOS ESTÁTICOS
# ============================
# 1. Configurar Jinja2 (carpeta de plantillas HTML)
templates = Jinja2Templates(directory="templates")

# 2. Montar archivos estáticos (CSS, JS, imágenes) en /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. Ruta raíz: sirve el index.html renderizado con Jinja2
@app.get("/")
async def serve_frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ============================
# ROUTERS DE LA API
# ============================
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(warehouse.router)
app.include_router(pos.router)
app.include_router(cash.router)
app.include_router(suppliers.router)
app.include_router(clients.router)

# ============================
# ENDPOINTS ADICIONALES
# ============================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "database": "connected"}

@app.get("/system/info")
async def system_info(db: Session = Depends(get_db)):
    try:
        from models.user_models import User
        from models.inventory_models import Product, POSLocation
        from models.cash_models import Sale

        total_users = db.query(User).count()
        total_products = db.query(Product).count()
        total_pos_locations = db.query(POSLocation).count()
        total_sales = db.query(Sale).count()
        today = datetime.now().date()
        today_sales = db.query(Sale).filter(Sale.sale_date >= today).count()

        return {
            "system": "Inventory Management System",
            "version": "1.0.0",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_users": total_users,
                "total_products": total_products,
                "total_pos_locations": total_pos_locations,
                "total_sales": total_sales,
                "today_sales": today_sales
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ============================
# MANEJADORES DE ERRORES GLOBALES
# ============================
@app.exception_handler(404)
async def not_found_exception_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Recurso no encontrado", "path": request.url.path}
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Error interno del servidor", "path": request.url.path}
    )

# ============================
# EJECUCIÓN (solo si se corre directamente)
# ============================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )