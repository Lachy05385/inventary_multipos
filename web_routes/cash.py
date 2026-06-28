from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.database import get_db
from web_app import templates, get_current_user_web
from models.user_models import User, UserRole
from models.cash_models import CashWithdrawalRequest, WithdrawalStatus, CashRegister, POSLocation

router = APIRouter()

@router.get("/cash/withdrawals", response_class=HTMLResponse)
async def withdrawals_list(
    request: Request,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        return RedirectResponse("/auth/login")
    
    # Consulta de retiros
    query = db.query(CashWithdrawalRequest)
    
    # Filtrar por estado
    if status:
        query = query.filter(CashWithdrawalRequest.status == WithdrawalStatus(status))
    
    # Restricciones por rol
    if current_user.role == UserRole.CASHIER:
        query = query.filter(CashWithdrawalRequest.cashier_id == current_user.id)
    elif current_user.role == UserRole.WAREHOUSE_MANAGER:
        # Gerentes pueden ver todos los retiros
        pass
    elif current_user.role == UserRole.ADMIN:
        # Admins pueden ver todos los retiros
        pass
    
    # Paginación
    page_size = 10
    offset = (page - 1) * page_size
    total_withdrawals = query.count()
    total_pages = (total_withdrawals + page_size - 1) // page_size
    
    withdrawals = query.order_by(desc(CashWithdrawalRequest.request_date)).offset(offset).limit(page_size).all()
    
    return templates.TemplateResponse(
        "cash/withdrawal_requests.html",
        {
            "request": request,
            "current_user": current_user,
            "withdrawals": withdrawals,
            "status_filter": status,
            "current_page": page,
            "total_pages": total_pages
        }
    )

@router.get("/cash/withdrawals/request", response_class=HTMLResponse)
async def new_withdrawal_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    if not current_user:
        return RedirectResponse("/auth/login")
    
    if current_user.role != UserRole.CASHIER:
        return RedirectResponse("/cash/withdrawals")
    
    # Obtener saldo actual de la caja
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == current_user.pos_location_id
    ).first()
    
    return templates.TemplateResponse(
        "cash/withdrawal_request_form.html",
        {
            "request": request,
            "current_user": current_user,
            "cash_register": cash_register
        }
    )

@router.post("/cash/withdrawals/request")
async def create_withdrawal_request(
    request: Request,
    amount: float = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    if not current_user or current_user.role != UserRole.CASHIER:
        return RedirectResponse("/auth/login")
    
    # Verificar saldo en caja
    cash_register = db.query(CashRegister).filter(
        CashRegister.pos_location_id == current_user.pos_location_id
    ).first()
    
    if not cash_register or cash_register.current_balance < amount:
        return templates.TemplateResponse(
            "cash/withdrawal_request_form.html",
            {
                "request": request,
                "current_user": current_user,
                "cash_register": cash_register,
                "error": "Saldo insuficiente en caja"
            }
        )
    
    # Crear solicitud de retiro
    withdrawal_request = CashWithdrawalRequest(
        pos_location_id=current_user.pos_location_id,
        cashier_id=current_user.id,
        amount=amount,
        reason=reason,
        status=WithdrawalStatus.PENDING
    )
    
    db.add(withdrawal_request)
    db.commit()
    
    return RedirectResponse("/cash/withdrawals", status_code=302)