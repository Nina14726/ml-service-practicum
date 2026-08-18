from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_session, service_error
from src.models import UserORM
from src.schemas import BalanceResponse, TopUpRequest
from src.services import top_up_balance

router = APIRouter()


@router.get("/balance", response_model=BalanceResponse)
def get_balance(user: UserORM = Depends(get_current_user)):
    return BalanceResponse(user_id=user.id, amount=user.balance.amount)


@router.post("/balance/top-up", response_model=BalanceResponse)
def top_up(
    payload: TopUpRequest,
    user: UserORM = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        top_up_balance(session, user.id, payload.amount)
        session.refresh(user.balance)
        return BalanceResponse(user_id=user.id, amount=user.balance.amount)
    except ValueError as error:
        raise service_error(error) from error
