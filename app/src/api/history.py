from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_session
from src.models import UserORM
from src.schemas import RequestHistoryResponse, TransactionResponse
from src.services import get_request_history, get_transaction_history

router = APIRouter()


@router.get("/history/requests", response_model=list[RequestHistoryResponse])
def request_history(user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    return get_request_history(session, user.id)


@router.get("/history/transactions", response_model=list[TransactionResponse])
def transaction_history(user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    return get_transaction_history(session, user.id)
