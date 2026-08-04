from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=4)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    created_at: datetime


class BalanceResponse(BaseModel):
    user_id: int
    amount: Decimal


class TopUpRequest(BaseModel):
    amount: Decimal = Field(gt=0)


class PredictionRequest(BaseModel):
    model_id: int
    data: list[dict]


class PredictionResponse(BaseModel):
    request_id: str
    status: str
    predictions: list
    invalid_data: list[dict]
    charged_credits: Decimal


class AsyncPredictionRequest(BaseModel):
    features: dict[str, float]
    model: str = Field(min_length=1)


class AsyncPredictionAccepted(BaseModel):
    task_id: str
    status: str


class AsyncPredictionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    features: dict
    model: str
    prediction: float | None
    worker_id: str | None
    status: str
    error: str | None
    created_at: datetime
    processed_at: datetime | None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transaction_type: str
    amount: Decimal
    request_id: str | None
    created_at: datetime


class RequestHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_id: int
    status: str
    predictions: list
    invalid_data: list[dict]
    charged_credits: Decimal
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
