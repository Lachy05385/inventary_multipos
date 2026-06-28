from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
from models.user_models import User, UserRole
from database.database import get_db
from routers.auth import get_current_user as get_current_user_api

# Configuración de templates
templates = Jinja2Templates(directory="templates")

# Función para obtener usuario actual en web
async def get_current_user_web(request: Request, db: Session = Depends(get_db)):
    """
    Obtiene el usuario actual para la interfaz web
    """
    # En una aplicación real, usarías cookies o sesiones
    # Por ahora, simularemos con un usuario por defecto para desarrollo
    try:
        # Intentar obtener usuario del token si existe
        token = request.cookies.get("access_token")
        if token:
            user = await get_current_user_api(token=token, db=db)
            return user
    except:
        pass
    
    # Para desarrollo, retornar un usuario por defecto
    
    user = db.query(User).filter(User.username == "admin").first()
    return user

# Función para verificar autenticación
async def require_auth(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})
    print(current_user)
    return current_user