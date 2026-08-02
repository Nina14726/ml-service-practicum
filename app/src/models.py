from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    balance: Mapped[BalanceORM] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    transactions: Mapped[list[TransactionORM]] = relationship(back_populates="user")
    requests: Mapped[list[MLRequestORM]] = relationship(back_populates="user")


class BalanceORM(Base):
    __tablename__ = "balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    user: Mapped[UserORM] = relationship(back_populates="balance")


class MLModelORM(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    prediction_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    requests: Mapped[list[MLRequestORM]] = relationship(back_populates="model")


class MLRequestORM(Base):
    __tablename__ = "ml_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    model_id: Mapped[int] = mapped_column(ForeignKey("ml_models.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="created", nullable=False)
    input_data: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    predictions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    invalid_data: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    charged_credits: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped[UserORM] = relationship(back_populates="requests")
    model: Mapped[MLModelORM] = relationship(back_populates="requests")
    transactions: Mapped[list[TransactionORM]] = relationship(back_populates="request")


class TransactionORM(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    request_id: Mapped[str | None] = mapped_column(
        ForeignKey("ml_requests.id"), nullable=True
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped[UserORM] = relationship(back_populates="transactions")
    request: Mapped[MLRequestORM | None] = relationship(back_populates="transactions")
