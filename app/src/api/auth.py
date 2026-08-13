from secrets import token_urlsafe

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import TOKENS, get_current_user, get_session, service_error
from src.models import UserORM
from src.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from src.services import authenticate_user, create_user

router = APIRouter()


@router.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    try:
        return create_user(session, payload.email, payload.password)
    except ValueError as error:
        raise service_error(error) from error


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    try:
        user = authenticate_user(session, payload.email, payload.password)
    except ValueError as error:
        raise service_error(error) from error
    token = token_urlsafe(32)
    TOKENS[token] = user.id
    return TokenResponse(access_token=token)


@router.get("/users/me", response_model=UserResponse)
def current_user(user: UserORM = Depends(get_current_user)):
    return user
