from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from database.database import get_db
from web_app import templates
from models.user_models import User
from routers.auth import authenticate_user, create_access_token, verify_password

router = APIRouter()

@router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/auth/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "Usuario o contraseña incorrectos"
            }
        )
    
    # Verificar si el usuario está activo y verificado
    if not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "La cuenta no está activa. Contacta al administrador."
            }
        )
    
    if not user.is_verified:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "La cuenta no está verificada. Verifica tu email antes de iniciar sesión."
            }
        )
    
    # Crear token de acceso
    access_token = create_access_token(data={"sub": user.username})
    
    # Redirigir al dashboard
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=1800  # 30 minutos
    )
    
    return response

@router.get("/auth/logout")
async def logout():
    response = RedirectResponse("/auth/login")
    response.delete_cookie("access_token")
    return response