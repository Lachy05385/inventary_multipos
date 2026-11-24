from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from database.database import get_db
from models.user_models import User, UserRole
from models.cash_models import CashRegister, CashWithdrawal
from models.cash_models import CashWithdrawalRequest  # asumo que existe el modelo
from schemas.cash_schemas import (
    CashWithdrawalCreate,
    CashWithdrawal as CashWithdrawalSchema,
    CashWithdrawalWithDetails,
    CashRegister as CashRegisterSchema,
    CashRegisterWithLocation,
    CashWithdrawalRequestCreate,
    CashWithdrawalRequestUpdate,
    CashWithdrawalRequestAuthorize,
    CashWithdrawalRequest as CashWithdrawalRequestSchema,
    CashWithdrawalRequestWithDetails,
    WithdrawalStatus,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/cash", tags=["cash"])


# ==================== DEPENDENCIAS DE ROL ====================

def get_admin_or_warehouse(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(403, "Solo administradores o gerentes de almacén")
    return current_user


def get_cashier_only(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.CASHIER:
        raise HTTPException(403, "Solo los cajeros pueden realizar esta acción")
    return current_user


# ==================== CAJA REGISTRADORA ====================
@router.get("/registers/summary")
def get_registers_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resumen de todas las cajas registradoras (solo admin/warehouse).
    Devuelve el balance actual por POS y el total general.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(403, "Solo administradores o gerentes de almacén")

    registers = db.query(CashRegister).options(
        joinedload(CashRegister.pos_location)
    ).all()

    total_general = 0.0
    detalle = []

    for r in registers:
        pos_name = r.pos_location.name if r.pos_location else f"POS #{r.pos_location_id}"
        detalle.append({
            "id": r.id,
            "pos_location_id": r.pos_location_id,
            "pos_name": pos_name,
            "current_balance": float(r.current_balance or 0.0),
            "last_updated": r.last_updated.isoformat() if r.last_updated else None,
        })
        total_general += float(r.current_balance or 0.0)

    return {
        "total_cash": round(total_general, 2),
        "registers_count": len(detalle),
        "registers": detalle,
    }




from sqlalchemy.orm import joinedload
from models.user_models import User, UserRole



@router.get("/cash/registers", response_model=List[CashRegisterWithLocation])
def read_cash_registers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista todas las cajas registradoras.
    - Admin y warehouse: pueden ver todas.
    - Cashier: solo ve la de su POS.
    """
    if current_user.role == UserRole.CASHIER:
        if not current_user.pos_location_id:
            return []
        registers = db.query(CashRegister).options(
            joinedload(CashRegister.pos_location)
        ).filter(CashRegister.pos_location_id == current_user.pos_location_id).all()
    else:
        registers = db.query(CashRegister).options(
            joinedload(CashRegister.pos_location)
        ).all()

    return registers


@router.get("/register/{pos_id}", response_model=CashRegisterWithLocation)
def read_cash_register(
    pos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ver la caja de un POS específico.
    - Cashier: solo su POS.
    - Admin y warehouse: cualquiera.
    """
    if current_user.role == UserRole.CASHIER and current_user.pos_location_id != pos_id:
        raise HTTPException(403, "No tienes acceso a esta caja")

    register = db.query(CashRegister).options(
        joinedload(CashRegister.pos_location)
    ).filter(CashRegister.pos_location_id == pos_id).first()

    if not register:
        raise HTTPException(404, "Caja registradora no encontrada")

    return register


# ==================== RETIROS DIRECTOS (solo admin/warehouse) ====================

@router.post("/withdraw", response_model=CashWithdrawalWithDetails)
def create_cash_withdrawal(
    withdrawal: CashWithdrawalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse),
):
    """
    Retiro directo de efectivo (sin solicitud previa).
    Solo admin o warehouse. Para el flujo normal, usar las solicitudes.
    """
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == withdrawal.pos_location_id
    ).first()

    if not cash_register:
        raise HTTPException(404, "Caja registradora no encontrada")

    if cash_register.current_balance < withdrawal.amount:
        raise HTTPException(
            400,
            f"Saldo insuficiente. Disponible: {cash_register.current_balance}"
        )

    db_withdrawal = CashWithdrawal(
        cash_register_id=cash_register.id,
        user_id=current_user.id,
        amount=withdrawal.amount,
        reason=withdrawal.reason,
    )

    cash_register.current_balance -= withdrawal.amount

    db.add(db_withdrawal)
    db.commit()
    db.refresh(db_withdrawal)

    return CashWithdrawalWithDetails(
        id=db_withdrawal.id,
        pos_location_id=withdrawal.pos_location_id,
        amount=db_withdrawal.amount,
        reason=db_withdrawal.reason,
        cash_register_id=db_withdrawal.cash_register_id,
        user_id=db_withdrawal.user_id,
        withdrawal_date=db_withdrawal.withdrawal_date,
        user_name=current_user.full_name,
        pos_location_name=cash_register.pos_location.name,
    )


@router.get("/withdrawals", response_model=List[CashWithdrawalWithDetails])
def read_cash_withdrawals(
    skip: int = 0,
    limit: int = 100,
    pos_location_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista retiros directos.
    - Admin y warehouse: todos.
    - Cashier: solo los de su POS.
    """
    query = db.query(CashWithdrawal).options(
        joinedload(CashWithdrawal.cash_register).joinedload(CashRegister.pos_location),
        joinedload(CashWithdrawal.user),
    )

    if current_user.role == UserRole.CASHIER:
        if not current_user.pos_location_id:
            return []
        query = query.join(CashRegister).filter(
            CashRegister.pos_location_id == current_user.pos_location_id
        )
    elif pos_location_id:
        query = query.join(CashRegister).filter(
            CashRegister.pos_location_id == pos_location_id
        )

    withdrawals = query.offset(skip).limit(limit).all()

    result = []
    for w in withdrawals:
        result.append(CashWithdrawalWithDetails(
            id=w.id,
            pos_location_id=w.cash_register.pos_location_id,
            amount=w.amount,
            reason=w.reason,
            cash_register_id=w.cash_register_id,
            user_id=w.user_id,
            withdrawal_date=w.withdrawal_date,
            user_name=w.user.full_name,
            pos_location_name=w.cash_register.pos_location.name,
        ))

    return result


# ==================== SOLICITUDES DE RETIRO ====================

@router.post("/withdrawal-requests", response_model=CashWithdrawalRequestWithDetails)
def create_withdrawal_request(
    data: CashWithdrawalRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_cashier_only),
):
    """
    El cashier solicita un retiro para su POS.
    """
    if current_user.pos_location_id != data.pos_location_id:
        raise HTTPException(403, "Solo puedes solicitar retiros de tu propio POS")

    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == data.pos_location_id
    ).first()
    if not cash_register:
        raise HTTPException(404, "Caja registradora no encontrada")

    if cash_register.current_balance < data.amount:
        raise HTTPException(
            400,
            f"Saldo insuficiente. Disponible: {cash_register.current_balance}"
        )

    request = CashWithdrawalRequest(
        pos_location_id=data.pos_location_id,
        cashier_id=current_user.id,
        amount=data.amount,
        reason=data.reason,
        status=WithdrawalStatus.PENDING,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return CashWithdrawalRequestWithDetails(
        id=request.id,
        pos_location_id=request.pos_location_id,
        amount=request.amount,
        reason=request.reason,
        cashier_id=request.cashier_id,
        authorizer_id=request.authorizer_id,
        status=request.status,
        request_date=request.request_date,
        authorized_date=request.authorized_date,
        completed_date=request.completed_date,
        rejection_reason=request.rejection_reason,
        cashier_name=current_user.full_name,
        authorizer_name=None,
        pos_location_name=cash_register.pos_location.name,
    )


@router.get("/withdrawal-requests", response_model=List[CashWithdrawalRequestWithDetails])
def read_withdrawal_requests(
    status: Optional[str] = Query(None, description="pending, approved, rejected, completed"),
    pos_location_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista solicitudes de retiro.
    - Cashier: solo las de su POS.
    - Admin y warehouse: todas.
    """
    query = db.query(CashWithdrawalRequest).options(
        joinedload(CashWithdrawalRequest.cash_register).joinedload(CashRegister.pos_location),
        joinedload(CashWithdrawalRequest.cashier),
        joinedload(CashWithdrawalRequest.authorizer),
    )

    if current_user.role == UserRole.CASHIER:
        if not current_user.pos_location_id:
            return []
        query = query.filter(
            CashWithdrawalRequest.pos_location_id == current_user.pos_location_id
        )
    elif pos_location_id:
        query = query.filter(CashWithdrawalRequest.pos_location_id == pos_location_id)

    if status:
        query = query.filter(CashWithdrawalRequest.status == status)

    requests = query.order_by(CashWithdrawalRequest.request_date.desc()).offset(skip).limit(limit).all()

    result = []
    for r in requests:
        result.append(CashWithdrawalRequestWithDetails(
            id=r.id,
            pos_location_id=r.pos_location_id,
            amount=r.amount,
            reason=r.reason,
            cashier_id=r.cashier_id,
            authorizer_id=r.authorizer_id,
            status=r.status,
            request_date=r.request_date,
            authorized_date=r.authorized_date,
            completed_date=r.completed_date,
            rejection_reason=r.rejection_reason,
            cashier_name=r.cashier.full_name,
            authorizer_name=r.authorizer.full_name if r.authorizer else None,
            pos_location_name=r.cash_register.pos_location.name if r.cash_register else "",
        ))

    return result


@router.put("/withdrawal-requests/{request_id}/authorize", response_model=CashWithdrawalRequestWithDetails)
def authorize_withdrawal_request(
    request_id: int,
    data: CashWithdrawalRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_warehouse),
):
    """
    Admin o warehouse autorizan o rechazan una solicitud.
    """
    request = db.query(CashWithdrawalRequest).filter(
        CashWithdrawalRequest.id == request_id
    ).first()
    if not request:
        raise HTTPException(404, "Solicitud no encontrada")

    if request.status != WithdrawalStatus.PENDING:
        raise HTTPException(400, "La solicitud ya fue procesada")

    if data.status == WithdrawalStatus.APPROVED:
        # Verificar saldo y descontar
        register = db.query(CashRegister).filter(
            CashRegister.pos_location_id == request.pos_location_id
        ).first()
        if not register:
            raise HTTPException(404, "Caja registradora no encontrada")
        if register.current_balance < request.amount:
            raise HTTPException(400, "Saldo insuficiente en caja")

        register.current_balance -= request.amount
        request.status = WithdrawalStatus.APPROVED
        request.authorizer_id = current_user.id
        request.authorized_date = datetime.utcnow()

    elif data.status == WithdrawalStatus.REJECTED:
        request.status = WithdrawalStatus.REJECTED
        request.authorizer_id = current_user.id
        request.authorized_date = datetime.utcnow()
        request.rejection_reason = data.rejection_reason

    else:
        raise HTTPException(400, "Estado no válido. Use 'approved' o 'rejected'")

    db.commit()
    db.refresh(request)

    return CashWithdrawalRequestWithDetails(
        id=request.id,
        pos_location_id=request.pos_location_id,
        amount=request.amount,
        reason=request.reason,
        cashier_id=request.cashier_id,
        authorizer_id=request.authorizer_id,
        status=request.status,
        request_date=request.request_date,
        authorized_date=request.authorized_date,
        completed_date=request.completed_date,
        rejection_reason=request.rejection_reason,
        cashier_name=request.cashier.full_name,
        authorizer_name=current_user.full_name,
        pos_location_name=request.cash_register.pos_location.name if request.cash_register else "",
    )