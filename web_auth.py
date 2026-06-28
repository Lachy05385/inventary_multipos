# web_auth.py
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from models.user_models import User

# Simulación simple de sesión para desarrollo
current_user_session = None

def get_current_user_web(request: Request, db: Session = Depends(get_db)):
    """Obtener usuario actual para la web (simulado para desarrollo)"""
    global current_user_session
    
    # Para desarrollo, si hay sesión simulada, usarla
    if current_user_session:
        user = db.query(User).filter(User.username == current_user_session).first()
        if user:
            return user
    
    # Si no hay sesión, retornar None (no autenticado)
    return None

def require_auth_web(current_user = Depends(get_current_user_web)):
    """Requerir autenticación para rutas web"""
    if not current_user:
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})
    return current_user

def set_current_user(username: str):
    """Establecer usuario actual (simulado)"""
    global current_user_session
    current_user_session = username

def clear_current_user():
    """Limpiar usuario actual (simulado)"""
    global current_user_session
    current_user_session = None