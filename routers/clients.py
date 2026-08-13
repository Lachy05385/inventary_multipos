# routers/clients.py
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from fastapi_mail import MessageSchema, MessageType
import secrets

from database.database import get_db
from models.client_models import Client as ClientModel, DeliveryAddress
from schemas.client_schemas import (
    ClientCreate,
    Client as ClientSchema,
    ClientLogin,
    ClientToken,
    ClientUpdate,
    DeliveryAddressCreate,
    DeliveryAddress as DeliveryAddressSchema
)
from routers.auth import (
    hash_password,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
    oauth2_scheme
)
from config.email import fm

router = APIRouter(prefix="/clients", tags=["clients"])

# ========== DEPENDENCIA PARA OBTENER CLIENTE AUTENTICADO ==========
async def get_current_client(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    client = db.query(ClientModel).filter(ClientModel.email == email).first()
    if client is None:
        raise credentials_exception
    return client

# ========== FUNCIÓN PARA ENVIAR EMAIL DE VERIFICACIÓN ==========
def send_verification_email(email: str, full_name: str, token: str):
    verification_link = f"http://localhost:8000/clients/verify?token={token}"
    message = MessageSchema(
        subject="Verifica tu correo electrónico",
        recipients=[email],
        body=f"""
        <h2>Hola {full_name}!</h2>
        <p>Gracias por registrarte. Haz clic en el siguiente enlace para verificar tu cuenta:</p>
        <p><a href="{verification_link}">{verification_link}</a></p>
        <p>Este enlace expirará en 24 horas.</p>
        <p>Si no solicitaste este registro, ignora este mensaje.</p>
        """,
        subtype=MessageType.html
    )
    fm.send_message(message)

# ========== REGISTRO PÚBLICO (CON VERIFICACIÓN POR EMAIL) ==========
@router.post("/register", response_model=ClientSchema)
def register_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db),
    background_tasks: Optional[BackgroundTasks] = None  # ⬅️ Opcional con default
):


    existing = db.query(ClientModel).filter(ClientModel.email == client_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    verification_token = secrets.token_urlsafe(32)

    db_client = ClientModel(
        email=client_data.email,
        full_name=client_data.full_name,
        phone=client_data.phone,
        password_hash=hash_password(client_data.password),
        is_verified=False,
        verification_token=verification_token
    )
    db.add(db_client)
    db.flush()

    if client_data.address:
        address = DeliveryAddress(
            client_id=db_client.id,
            **client_data.address.model_dump()
        )
        db.add(address)

    db.commit()
    db.refresh(db_client)

    background_tasks.add_task(
        send_verification_email,
        db_client.email,
        db_client.full_name,
        verification_token
    )

    return db_client

# ========== VERIFICAR EMAIL ==========
@router.get("/verify", response_model=dict)
def verify_email(
    token: str = Query(..., description="Token de verificación"),
    db: Session = Depends(get_db)
):
    client = db.query(ClientModel).filter(ClientModel.verification_token == token).first()
    if not client:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    if client.is_verified:
        return {"message": "Email already verified"}
    if client.created_at < datetime.now() - timedelta(hours=24):
        raise HTTPException(status_code=400, detail="Verification token expired")

    client.is_verified = True
    client.verification_token = None
    client.verified_at = datetime.now()
    db.commit()

    return {"message": "Email verified successfully"}

# ========== REENVIAR EMAIL DE VERIFICACIÓN ==========
@router.post("/resend-verification", response_model=dict)
def resend_verification(
    email: str = Query(..., description="Email del cliente"),
    db: Session = Depends(get_db),
    background_tasks: Optional[BackgroundTasks]=None
):
    client = db.query(ClientModel).filter(ClientModel.email == email).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if client.is_verified:
        return {"message": "Email already verified"}

    new_token = secrets.token_urlsafe(32)
    client.verification_token = new_token
    db.commit()

    background_tasks.add_task(
        send_verification_email,
        client.email,
        client.full_name,
        new_token
    )

    return {"message": "Verification email resent"}

# ========== LOGIN DE CLIENTE ==========
@router.post("/login", response_model=ClientToken)
def login_client(
    login_data: ClientLogin,
    db: Session = Depends(get_db)
):
    client = db.query(ClientModel).filter(ClientModel.email == login_data.email).first()
    if not client:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not client.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please verify your email first.")
    if not verify_password(login_data.password, client.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": client.email, "client_id": client.id},
        expires_delta=access_token_expires
    )

    return ClientToken(
        access_token=access_token,
        token_type="bearer",
        client=client
    )

# ========== OBTENER PERFIL ==========
@router.get("/me", response_model=ClientSchema)
def get_client_profile(
    current_client: ClientModel = Depends(get_current_client)
):
    return current_client

# ========== ACTUALIZAR PERFIL ==========
@router.put("/me", response_model=ClientSchema)
def update_client_profile(
    client_update: ClientUpdate,
    db: Session = Depends(get_db),
    current_client: ClientModel = Depends(get_current_client)
):
    update_data = client_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_client, field, value)
    db.commit()
    db.refresh(current_client)
    return current_client

# ========== AGREGAR DIRECCIÓN ==========
@router.post("/me/addresses", response_model=DeliveryAddressSchema)
def add_delivery_address(
    address: DeliveryAddressCreate,
    db: Session = Depends(get_db),
    current_client: ClientModel = Depends(get_current_client)
):
    if address.is_default:
        db.query(DeliveryAddress).filter(
            DeliveryAddress.client_id == current_client.id
        ).update({"is_default": False})

    db_address = DeliveryAddress(
        client_id=current_client.id,
        **address.model_dump()
    )
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

# ========== LISTAR DIRECCIONES ==========
@router.get("/me/addresses", response_model=List[DeliveryAddressSchema])
def get_client_addresses(
    db: Session = Depends(get_db),
    current_client: ClientModel = Depends(get_current_client)
):
    return current_client.addresses