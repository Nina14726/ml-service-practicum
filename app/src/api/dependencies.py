from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models import UserORM

TOKENS: dict[str, int] = {}


def get_session():
    with SessionLocal() as session:
        yield session


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> UserORM:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = TOKENS.get(token)
    user = session.get(UserORM, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid access token")
    return user


def service_error(error: ValueError) -> HTTPException:
    message = str(error)
    if message == "Insufficient balance":
        code = status.HTTP_402_PAYMENT_REQUIRED
    elif message == "User already exists":
        code = status.HTTP_409_CONFLICT
    elif message in {"ML model not found", "Balance not found"}:
        code = status.HTTP_404_NOT_FOUND
    elif message == "Invalid email or password":
        code = status.HTTP_401_UNAUTHORIZED
    else:
        code = status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail=message)
