from contextlib import asynccontextmanager
from datetime import datetime, timezone
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.init_db import init_database
from src.models import PredictionTaskORM, UserORM
from src.rabbitmq import publish_task
from src.schemas import (
    AsyncPredictionAccepted,
    AsyncPredictionRequest,
    AsyncPredictionResult,
    BalanceResponse,
    LoginRequest,
    PredictionRequest,
    PredictionResponse,
    RegisterRequest,
    RequestHistoryResponse,
    TokenResponse,
    TopUpRequest,
    TransactionResponse,
    UserResponse,
)
from src.services import (
    authenticate_user,
    create_user,
    get_request_history,
    get_transaction_history,
    run_prediction,
    top_up_balance,
)

TOKENS: dict[str, int] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="ML Service", lifespan=lifespan)


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


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "ML service is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    try:
        return create_user(session, payload.email, payload.password)
    except ValueError as error:
        raise service_error(error) from error


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    try:
        user = authenticate_user(session, payload.email, payload.password)
    except ValueError as error:
        raise service_error(error) from error
    token = token_urlsafe(32)
    TOKENS[token] = user.id
    return TokenResponse(access_token=token)


@app.get("/users/me", response_model=UserResponse)
def current_user(user: UserORM = Depends(get_current_user)):
    return user


@app.get("/balance", response_model=BalanceResponse)
def get_balance(user: UserORM = Depends(get_current_user)):
    return BalanceResponse(user_id=user.id, amount=user.balance.amount)


@app.post("/balance/top-up", response_model=BalanceResponse)
def top_up(payload: TopUpRequest, user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        top_up_balance(session, user.id, payload.amount)
        session.refresh(user.balance)
        return BalanceResponse(user_id=user.id, amount=user.balance.amount)
    except ValueError as error:
        raise service_error(error) from error


@app.post("/predict", response_model=AsyncPredictionAccepted, status_code=202)
def enqueue_prediction(payload: AsyncPredictionRequest, session: Session = Depends(get_session)):
    task_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    task = PredictionTaskORM(
        task_id=task_id,
        features=payload.features,
        model=payload.model,
        status="queued",
        created_at=created_at,
    )
    session.add(task)
    session.commit()

    message = {
        "task_id": task_id,
        "features": payload.features,
        "model": payload.model,
        "timestamp": created_at.isoformat(),
    }
    try:
        publish_task(message)
    except Exception as error:
        task.status = "failed"
        task.error = f"publish error: {error}"
        session.commit()
        raise HTTPException(status_code=503, detail="RabbitMQ is unavailable") from error

    return AsyncPredictionAccepted(task_id=task_id, status="queued")


@app.get("/predict/{task_id}", response_model=AsyncPredictionResult)
def get_prediction_result(task_id: str, session: Session = Depends(get_session)):
    task = session.get(PredictionTaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Prediction task not found")
    return task


@app.post("/predict/sync", response_model=PredictionResponse)
def predict_sync(payload: PredictionRequest, user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        request = run_prediction(session, user.id, payload.model_id, payload.data)
    except ValueError as error:
        raise service_error(error) from error
    return PredictionResponse(
        request_id=request.id,
        status=request.status,
        predictions=request.predictions,
        invalid_data=request.invalid_data,
        charged_credits=request.charged_credits,
    )


@app.get("/history/requests", response_model=list[RequestHistoryResponse])
def request_history(user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    return get_request_history(session, user.id)


@app.get("/history/transactions", response_model=list[TransactionResponse])
def transaction_history(user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    return get_transaction_history(session, user.id)
