from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from models.user_models import User, UserRole
from schemas.user_schemas import UserCreate, User as UserSchema
from routers.auth import get_current_user, get_password_hash

router = APIRouter(prefix="/users", tags=["users"])

from fastapi.responses import FileResponse






# Dependency para verificar si es admin
def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

@router.post("/", response_model=UserSchema)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role,
        pos_location_id=user.pos_location_id
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[UserSchema])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

from schemas.user_schemas import UserUpdate  # asegúrate de importarlo

@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificar username único (si se cambia)
    if user_update.username and user_update.username != db_user.username:
        existe = db.query(User).filter(User.username == user_update.username).first()
        if existe:
            raise HTTPException(status_code=400, detail="Username ya registrado")
        db_user.username = user_update.username

    # Verificar email único (si se cambia)
    if user_update.email and user_update.email != db_user.email:
        existe = db.query(User).filter(User.email == user_update.email).first()
        if existe:
            raise HTTPException(status_code=400, detail="Email ya registrado")
        db_user.email = user_update.email

    # Actualizar campos simples
    if user_update.full_name is not None:
        db_user.full_name = user_update.full_name
    if user_update.role is not None:
        db_user.role = user_update.role
    if user_update.pos_location_id is not None:
        db_user.pos_location_id = user_update.pos_location_id

    # Si se envía nueva contraseña, actualizarla
    if user_update.password and user_update.password.strip():
        db_user.hashed_password = get_password_hash(user_update.password)

    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(db_user)
    db.commit()
    return {"message": f"Usuario {db_user.username} eliminado correctamente"}