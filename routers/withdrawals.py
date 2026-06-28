from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from database.database import get_db
from models.user_models import User, UserRole
from models.cash_models import CashWithdrawalRequest, WithdrawalStatus, CashRegister
from models.inventory_models import POSLocation
from schemas.cash_schemas import (
    CashWithdrawalRequestCreate, 
    CashWithdrawalRequest as CashWithdrawalRequestSchema,
    CashWithdrawalRequestWithDetails,
    CashWithdrawalRequestUpdate,
    CashWithdrawalRequestAuthorize,
    CompleteWithdrawalRequest,
    WithdrawalStatus
)
from routers.auth import get_current_user

router = APIRouter(prefix="/withdrawals", tags=["cash-withdrawals"])

@router.post("/request", response_model=CashWithdrawalRequestWithDetails)
async def create_withdrawal_request(
    request: CashWithdrawalRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crear una nueva solicitud de retiro de efectivo
    """
    # Verificar que el usuario sea cajero y tenga acceso al POS
    if current_user.role != UserRole.CASHIER:
        raise HTTPException(
            status_code=403, 
            detail="Solo los cajeros pueden solicitar retiros"
        )
    
    if current_user.pos_location_id != request.pos_location_id:
        raise HTTPException(
            status_code=403, 
            detail="No tienes acceso a este punto de venta"
        )
    
    # Verificar que el POS existe
    pos_location = db.query(POSLocation).filter(
        POSLocation.id == request.pos_location_id
    ).first()
    if not pos_location:
        raise HTTPException(status_code=404, detail="Punto de venta no encontrado")
    
    # Verificar saldo en caja
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == request.pos_location_id
    ).first()
    
    if not cash_register:
        raise HTTPException(status_code=404, detail="Caja registradora no encontrada")
    
    if cash_register.current_balance < request.amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Saldo insuficiente en caja. Disponible: {cash_register.current_balance}"
        )
    
    # Crear solicitud de retiro
    withdrawal_request = CashWithdrawalRequest(
        pos_location_id=request.pos_location_id,
        cashier_id=current_user.id,
        amount=request.amount,
        reason=request.reason,
        status=WithdrawalStatus.PENDING
    )
    
    db.add(withdrawal_request)
    db.commit()
    db.refresh(withdrawal_request)
    
    # Construir respuesta con detalles
    return CashWithdrawalRequestWithDetails(
        id=withdrawal_request.id,
        pos_location_id=withdrawal_request.pos_location_id,
        cashier_id=withdrawal_request.cashier_id,
        authorizer_id=withdrawal_request.authorizer_id,
        amount=withdrawal_request.amount,
        reason=withdrawal_request.reason,
        status=withdrawal_request.status,
        request_date=withdrawal_request.request_date,
        authorized_date=withdrawal_request.authorized_date,
        completed_date=withdrawal_request.completed_date,
        rejection_reason=withdrawal_request.rejection_reason,
        cashier_name=current_user.full_name,
        authorizer_name=None,
        pos_location_name=pos_location.name
    )

@router.get("/my-requests", response_model=List[CashWithdrawalRequestWithDetails])
async def get_my_withdrawal_requests(
    status: Optional[WithdrawalStatus] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener las solicitudes de retiro del usuario actual
    """
    query = db.query(CashWithdrawalRequest).filter(
        CashWithdrawalRequest.cashier_id == current_user.id
    )
    
    if status:
        query = query.filter(CashWithdrawalRequest.status == status)
    
    requests = query.order_by(CashWithdrawalRequest.request_date.desc()).offset(skip).limit(limit).all()
    
    result = []
    for req in requests:
        result.append(CashWithdrawalRequestWithDetails(
            id=req.id,
            pos_location_id=req.pos_location_id,
            cashier_id=req.cashier_id,
            authorizer_id=req.authorizer_id,
            amount=req.amount,
            reason=req.reason,
            status=req.status,
            request_date=req.request_date,
            authorized_date=req.authorized_date,
            completed_date=req.completed_date,
            rejection_reason=req.rejection_reason,
            cashier_name=req.cashier.full_name,
            authorizer_name=req.authorizer.full_name if req.authorizer else None,
            pos_location_name=req.pos_location.name
        ))
    
    return result

@router.get("/pending", response_model=List[CashWithdrawalRequestWithDetails])
async def get_pending_withdrawal_requests(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener solicitudes de retiro pendientes (para administradores y gerentes)
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para ver solicitudes pendientes"
        )
    
    requests = db.query(CashWithdrawalRequest).filter(
        CashWithdrawalRequest.status == WithdrawalStatus.PENDING
    ).order_by(CashWithdrawalRequest.request_date.desc()).offset(skip).limit(limit).all()
    
    result = []
    for req in requests:
        result.append(CashWithdrawalRequestWithDetails(
            id=req.id,
            pos_location_id=req.pos_location_id,
            cashier_id=req.cashier_id,
            authorizer_id=req.authorizer_id,
            amount=req.amount,
            reason=req.reason,
            status=req.status,
            request_date=req.request_date,
            authorized_date=req.authorized_date,
            completed_date=req.completed_date,
            rejection_reason=req.rejection_reason,
            cashier_name=req.cashier.full_name,
            authorizer_name=req.authorizer.full_name if req.authorizer else None,
            pos_location_name=req.pos_location.name
        ))
    
    return result

@router.put("/{request_id}/authorize", response_model=CashWithdrawalRequestWithDetails)
async def authorize_withdrawal_request(
    request_id: int,
    auth_data: CashWithdrawalRequestAuthorize,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Autorizar o rechazar una solicitud de retiro
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para autorizar retiros"
        )
    
    withdrawal_request = db.query(CashWithdrawalRequest).filter(
        CashWithdrawalRequest.id == request_id
    ).first()
    
    if not withdrawal_request:
        raise HTTPException(status_code=404, detail="Solicitud de retiro no encontrada")
    
    if withdrawal_request.status != WithdrawalStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail="La solicitud ya fue procesada"
        )
    
    # Actualizar solicitud
    withdrawal_request.authorizer_id = current_user.id
    withdrawal_request.status = auth_data.status
    withdrawal_request.authorized_date = datetime.now()
    
    if auth_data.status == WithdrawalStatus.REJECTED:
        # En un caso real, aquí podrías pedir razón de rechazo
        withdrawal_request.rejection_reason = "Rechazado por el autorizador"
    
    db.commit()
    db.refresh(withdrawal_request)
    
    return CashWithdrawalRequestWithDetails(
        id=withdrawal_request.id,
        pos_location_id=withdrawal_request.pos_location_id,
        cashier_id=withdrawal_request.cashier_id,
        authorizer_id=withdrawal_request.authorizer_id,
        amount=withdrawal_request.amount,
        reason=withdrawal_request.reason,
        status=withdrawal_request.status,
        request_date=withdrawal_request.request_date,
        authorized_date=withdrawal_request.authorized_date,
        completed_date=withdrawal_request.completed_date,
        rejection_reason=withdrawal_request.rejection_reason,
        cashier_name=withdrawal_request.cashier.full_name,
        authorizer_name=current_user.full_name,
        pos_location_name=withdrawal_request.pos_location.name
    )

@router.post("/complete", response_model=CashWithdrawalRequestWithDetails)
async def complete_withdrawal(
    complete_data: CompleteWithdrawalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Completar un retiro autorizado (ejecutar el retiro de efectivo)
    """
    withdrawal_request = db.query(CashWithdrawalRequest).filter(
        CashWithdrawalRequest.id == complete_data.withdrawal_request_id
    ).first()
    
    if not withdrawal_request:
        raise HTTPException(status_code=404, detail="Solicitud de retiro no encontrada")
    
    # Verificar que el usuario tenga acceso al POS
    if (current_user.role == UserRole.CASHIER and 
        current_user.pos_location_id != withdrawal_request.pos_location_id):
        raise HTTPException(
            status_code=403, 
            detail="No tienes acceso a este punto de venta"
        )
    
    if withdrawal_request.status != WithdrawalStatus.APPROVED:
        raise HTTPException(
            status_code=400, 
            detail="Solo se pueden completar retiros aprobados"
        )
    
    # Verificar saldo en caja
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == withdrawal_request.pos_location_id
    ).first()
    
    if cash_register.current_balance < withdrawal_request.amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Saldo insuficiente en caja. Disponible: {cash_register.current_balance}"
        )
    
    # Ejecutar el retiro
    cash_register.current_balance -= withdrawal_request.amount
    withdrawal_request.status = WithdrawalStatus.COMPLETED
    withdrawal_request.completed_date = datetime.now()
    
    db.commit()
    db.refresh(withdrawal_request)
    
    return CashWithdrawalRequestWithDetails(
        id=withdrawal_request.id,
        pos_location_id=withdrawal_request.pos_location_id,
        cashier_id=withdrawal_request.cashier_id,
        authorizer_id=withdrawal_request.authorizer_id,
        amount=withdrawal_request.amount,
        reason=withdrawal_request.reason,
        status=withdrawal_request.status,
        request_date=withdrawal_request.request_date,
        authorized_date=withdrawal_request.authorized_date,
        completed_date=withdrawal_request.completed_date,
        rejection_reason=withdrawal_request.rejection_reason,
        cashier_name=withdrawal_request.cashier.full_name,
        authorizer_name=withdrawal_request.authorizer.full_name if withdrawal_request.authorizer else None,
        pos_location_name=withdrawal_request.pos_location.name
    )

@router.get("/pos/{pos_id}", response_model=List[CashWithdrawalRequestWithDetails])
async def get_withdrawals_by_pos(
    pos_id: int,
    status: Optional[WithdrawalStatus] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener retiros por punto de venta
    """
    # Verificar permisos
    if (current_user.role == UserRole.CASHIER and 
        current_user.pos_location_id != pos_id):
        raise HTTPException(
            status_code=403, 
            detail="No tienes acceso a este punto de venta"
        )
    
    query = db.query(CashWithdrawalRequest).filter(
        CashWithdrawalRequest.pos_location_id == pos_id
    )
    
    if status:
        query = query.filter(CashWithdrawalRequest.status == status)
    
    requests = query.order_by(CashWithdrawalRequest.request_date.desc()).offset(skip).limit(limit).all()
    
    result = []
    for req in requests:
        result.append(CashWithdrawalRequestWithDetails(
            id=req.id,
            pos_location_id=req.pos_location_id,
            cashier_id=req.cashier_id,
            authorizer_id=req.authorizer_id,
            amount=req.amount,
            reason=req.reason,
            status=req.status,
            request_date=req.request_date,
            authorized_date=req.authorized_date,
            completed_date=req.completed_date,
            rejection_reason=req.rejection_reason,
            cashier_name=req.cashier.full_name,
            authorizer_name=req.authorizer.full_name if req.authorizer else None,
            pos_location_name=req.pos_location.name
        ))
    
    return result