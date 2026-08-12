# routers/clients.py
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

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

# ========== REGISTRO PÚBLICO (NO AUTENTICADO) ==========
@router.post("/register", response_model=ClientSchema)
def register_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db)
):
    # Verificar si el email ya existe
    existing = db.query(ClientModel).filter(ClientModel.email == client_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Crear cliente (usar el modelo SQLAlchemy, NO el esquema Pydantic)
    db_client = ClientModel(
        email=client_data.email,
        full_name=client_data.full_name,
        phone=client_data.phone,
        password_hash=hash_password(client_data.password),
        is_verified=False
    )
    db.add(db_client)
    db.flush()  # Para obtener el id

    # Si se proporcionó dirección, crearla
    if client_data.address:
        address = DeliveryAddress(
            client_id=db_client.id,
            **client_data.address.model_dump()
        )
        db.add(address)

    db.commit()
    db.refresh(db_client)
    return db_client  # FastAPI convertirá automáticamente a ClientSchema gracias al response_model

# ========== LOGIN DE CLIENTE ==========
@router.post("/login", response_model=ClientToken)
def login_client(
    login_data: ClientLogin,
    db: Session = Depends(get_db)
):
    client = db.query(ClientModel).filter(ClientModel.email == login_data.email).first()
    if not client:
        raise HTTPException(status_code=401, detail="Invalid credentials")

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

# ========== OBTENER PERFIL DEL CLIENTE AUTENTICADO ==========
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

# ========== AGREGAR DIRECCIÓN DE ENTREGA ==========
@router.post("/me/addresses", response_model=DeliveryAddressSchema)
def add_delivery_address(
    address: DeliveryAddressCreate,
    db: Session = Depends(get_db),
    current_client: ClientModel = Depends(get_current_client)
):
    # Si es la primera dirección o is_default=True, asegurar que no haya otra default
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

# ========== LISTAR DIRECCIONES DEL CLIENTE ==========
@router.get("/me/addresses", response_model=List[DeliveryAddressSchema])
def get_client_addresses(
    db: Session = Depends(get_db),
    current_client: ClientModel = Depends(get_current_client)
):
    return current_client.addresses