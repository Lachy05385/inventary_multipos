from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime
import uvicorn
import os

# Importar componentes de la base de datos
from database.database import engine, Base, get_db

# Importar modelos para crear las tablas
from models.user_models import Base as UserBase
from models.inventory_models import Base as InventoryBase
from models.cash_models import Base as CashBase
from models.relationships1 import *

# Importar routers
from routers import auth, users, categories, warehouse, pos, cash, suppliers

# Crear todas las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Inicializar FastAPI
app = FastAPI(
    title="Sistema de Inventarios Multi-POS",
    description="""
    Sistema completo de gestión de inventarios para negocios con múltiples puntos de venta.
    
    ## Características
    * 🔐 Autenticación JWT con roles de usuario
    * 🏭 Gestión de Almacén Central 
    * 🏪 Puntos de Venta Múltiples
    * 📦 Control de Inventario en tiempo real
    * 💰 Gestión de Efectivo y cajas registradoras
    * 📊 Reportes y Dashboard
    """,
    version="1.0.0",
    contact={"name": "Soporte Técnico", "email": "soporte@inventarios.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
)

# ========== CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== ARCHIVOS ESTÁTICOS (SOLO UNA VEZ) ==========
# Verificar que el directorio existe
if not os.path.exists("static"):
    os.makedirs("static", exist_ok=True)
if not os.path.exists("static/templates"):
    os.makedirs("static/templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ========== ROUTERS ==========
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(warehouse.router)
app.include_router(pos.router)
app.include_router(cash.router)
app.include_router(suppliers.router)


# ========== PÁGINAS HTML ==========
@app.get("/", include_in_schema=False)
async def landing():
    return FileResponse("static/templates/index.html")

@app.get("/login", include_in_schema=False)
async def login_page():
    return FileResponse("static/templates/login.html")

@app.get("/usuarios", include_in_schema=False)
async def usuarios_page():
    return FileResponse("static/templates/usuarios.html")

@app.get("/inventario", include_in_schema=False)
async def inventario_page():
    return FileResponse("static/templates/inventario.html")

@app.get("/panel", include_in_schema=False)
async def inventario_page():
    return FileResponse("static/templates/panel.html")

@app.get("/portafolio", include_in_schema=False)
async def portafolio_page():
    return FileResponse("static/templates/portafolio.html")

# ========== HEALTH & INFO ==========
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving system info: {str(e)}"
        )

# ========== MIDDLEWARE DE LOGGING ==========
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds() * 1000
    print(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms")
    return response

# ========== MANEJO DE ERRORES ==========
# ⚠️ IMPORTANTE: Solo manejar 404 para rutas de API, no para archivos estáticos
@app.exception_handler(404)
async def not_found_exception_handler(request, exc):
    # Si la ruta empieza con /static, dejar que FastAPI maneje el 404 normalmente
    if request.url.path.startswith("/static"):
        return JSONResponse(
            status_code=404,
            content={"error": "Archivo no encontrado", "path": request.url.path}
        )
    return JSONResponse(
        status_code=404,
        content={
            "error": "Recurso no encontrado",
            "path": request.url.path,
            "message": "El endpoint solicitado no existe"
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "path": request.url.path,
            "message": "Ocurrió un error inesperado"
        }
    )

# ========== CONFIGURACIÓN PARA DESARROLLO ==========
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )