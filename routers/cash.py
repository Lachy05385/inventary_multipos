from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.database import get_db
from models.user_models import User, UserRole
from models.cash_models import CashRegister, CashWithdrawal
from schemas.cash_schemas import (
    CashWithdrawalCreate, CashWithdrawal as CashWithdrawalSchema, CashWithdrawalWithDetails,
    CashRegister as CashRegisterSchema, CashRegisterWithLocation
)
from routers.auth import get_current_user

router = APIRouter(prefix="/cash", tags=["cash"])

@router.get("/registers", response_model=List[CashRegisterWithLocation])
def read_cash_registers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    registers = db.query(CashRegister).all()
    
    
    
    return registers

@router.get("/register/{pos_id}", response_model=CashRegisterWithLocation)
def read_cash_register(
    pos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Solo admin o usuarios de ese POS pueden ver la caja
    if (current_user.role == UserRole.CASHIER and 
        current_user.pos_location_id != pos_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == pos_id
    ).first()
    
    if not register:
        raise HTTPException(status_code=404, detail="Cash register not found")
    
    return CashRegisterWithLocation(
        id=register.id,
        pos_location_id=register.pos_location_id,
        current_balance=register.current_balance,
        last_updated=register.last_updated,
        pos_location=register.pos_location.name
    )

@router.post("/withdraw", response_model=CashWithdrawalWithDetails)
def create_cash_withdrawal(
    withdrawal: CashWithdrawalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar permisos
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Verificar caja registradora
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == withdrawal.pos_location_id
    ).first()
    
    if not cash_register:
        raise HTTPException(status_code=404, detail="Cash register not found")
    
    # Verificar saldo suficiente
    if cash_register.current_balance < withdrawal.amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient cash in register. Available: {cash_register.current_balance}"
        )
    
    # Crear retiro
    db_withdrawal = CashWithdrawal(
        cash_register_id=cash_register.id,
        user_id=current_user.id,
        amount=withdrawal.amount,
        reason=withdrawal.reason
    )
    
    # Actualizar saldo de caja
    cash_register.current_balance -= withdrawal.amount
    
    db.add(db_withdrawal)
    db.commit()
    db.refresh(db_withdrawal)
    
    # Construir respuesta con detalles
    withdrawal_with_details = CashWithdrawalWithDetails(
        id=db_withdrawal.id,
        pos_location_id=withdrawal.pos_location_id,
        amount=db_withdrawal.amount,
        reason=db_withdrawal.reason,
        cash_register_id=db_withdrawal.cash_register_id,
        user_id=db_withdrawal.user_id,
        withdrawal_date=db_withdrawal.withdrawal_date,
        user_name=current_user.full_name,
        pos_location_name=cash_register.pos_location.name
    )
    
    return withdrawal_with_details

@router.get("/withdrawals", response_model=List[CashWithdrawalWithDetails])
def read_cash_withdrawals(
    skip: int = 0,
    limit: int = 100,
    pos_location_id: int = Query(None, description="Filter by POS location"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    query = db.query(CashWithdrawal)
    
    if pos_location_id:
        query = query.join(CashRegister).filter(
            CashRegister.pos_location_id == pos_location_id
        )
    
    withdrawals = query.offset(skip).limit(limit).all()
    
    result = []
    for withdrawal in withdrawals:
        result.append(CashWithdrawalWithDetails(
            id=withdrawal.id,
            pos_location_id=withdrawal.cash_register.pos_location_id,
            amount=withdrawal.amount,
            reason=withdrawal.reason,
            cash_register_id=withdrawal.cash_register_id,
            user_id=withdrawal.user_id,
            withdrawal_date=withdrawal.withdrawal_date,
            user_name=withdrawal.user.full_name,
            pos_location_name=withdrawal.cash_register.pos_location.name
        ))
    
    return result