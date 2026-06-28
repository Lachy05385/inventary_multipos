from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime
import uvicorn

# Importar componentes de la base de datos
from database.database import engine, Base, get_db

# Importar modelos para crear las tablas (sin relaciones primero)
from models.user_models import Base as UserBase
from models.inventory_models import Base as InventoryBase  
from models.cash_models import Base as CashBase

# Importar relaciones después de crear modelos
from models.relationships1 import *

# Importar routers
from routers import auth, users, warehouse, pos, cash

# Crear todas las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Inicializar FastAPI
app = FastAPI(
    title="Sistema de Inventarios Multi-POS",
    description="""
    Sistema completo de gestión de inventarios para negocios con múltiples puntos de venta.
    
    ## Características
    
    * 🔐 **Autenticación JWT** con roles de usuario
    * 🏭 **Gestión de Almacén Central** 
    * 🏪 **Puntos de Venta Múltiples**
    * 📦 **Control de Inventario** en tiempo real
    * 💰 **Gestión de Efectivo** y cajas registradoras
    * 📊 **Reportes y Dashboard**
    
    ## Roles de Usuario
    
    * **Admin**: Acceso completo al sistema
    * **Warehouse Manager**: Gestión de almacén y transferencias
    * **Cashier**: Ventas en punto de venta asignado
    """,
    version="1.0.0",
    contact={
        "name": "Soporte Técnico",
        "email": "soporte@inventarios.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(warehouse.router)
app.include_router(pos.router)
app.include_router(cash.router)

# Dependencia de autenticación para verificar token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

@app.get("/")
async def root():
    """
    Endpoint raíz que muestra información básica del sistema
    """
    return {
        "message": "Bienvenido al Sistema de Inventarios Multi-POS",
        "version": "1.0.0",
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "endpoints_available": [
            "/docs - Documentación interactiva",
            "/redoc - Documentación alternativa",
            "/auth/token - Login para obtener token",
            "/users/ - Gestión de usuarios",
            "/warehouse/ - Gestión de almacén",
            "/pos/ - Puntos de venta",
            "/cash/ - Gestión de efectivo"
        ]
    }

@app.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud del sistema
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }

@app.get("/system/info")
async def system_info(db: Session = Depends(get_db)):
    """
    Información general del sistema y estadísticas
    """
    try:
        from models.user_models import User
        from models.inventory_models import Product, POSLocation
        from models.cash_models import Sale
        
        total_users = db.query(User).count()
        total_products = db.query(Product).count()
        total_pos_locations = db.query(POSLocation).count()
        total_sales = db.query(Sale).count()
        
        # Calcular ventas del día
        today = datetime.now().date()
        today_sales = db.query(Sale).filter(
            Sale.sale_date >= today
        ).count()
        
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
            },
            "features": [
                "Multi-tenant architecture",
                "JWT authentication",
                "Role-based access control",
                "Real-time inventory tracking",
                "Cash management",
                "Sales reporting"
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving system info: {str(e)}"
        )

# Manejo de errores global
@app.exception_handler(404)
async def not_found_exception_handler(request, exc):
    return {
        "error": "Recurso no encontrado",
        "path": request.url.path,
        "message": "El endpoint solicitado no existe"
    }

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    return {
        "error": "Error interno del servidor",
        "path": request.url.path,
        "message": "Ocurrió un error inesperado"
    }

# Middleware para logging
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.now()
    
    response = await call_next(request)
    
    process_time = (datetime.now() - start_time).total_seconds() * 1000
    
    print(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms")
    
    return response

# Configuración para desarrollo
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )