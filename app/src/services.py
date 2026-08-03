from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import (
    BalanceORM,
    MLModelORM,
    MLRequestORM,
    TransactionORM,
    UserORM,
)


def create_user(
    session: Session,
    email: str,
    password_hash: str,
    role: str = "user",
    initial_balance: Decimal = Decimal("0.00"),
) -> UserORM:
    user = UserORM(email=email, password_hash=password_hash, role=role)
    user.balance = BalanceORM(amount=initial_balance)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_email(session: Session, email: str) -> UserORM | None:
    return session.scalar(select(UserORM).where(UserORM.email == email))


def top_up_balance(session: Session, user_id: int, amount: Decimal) -> TransactionORM:
    if amount <= 0:
        raise ValueError("Amount must be positive")

    balance = session.scalar(
        select(BalanceORM).where(BalanceORM.user_id == user_id).with_for_update()
    )
    if balance is None:
        raise ValueError("Balance not found")

    balance.amount += amount
    transaction = TransactionORM(
        user_id=user_id,
        transaction_type="credit",
        amount=amount,
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def debit_balance(
    session: Session,
    user_id: int,
    amount: Decimal,
    request_id: str | None = None,
) -> TransactionORM:
    if amount <= 0:
        raise ValueError("Amount must be positive")

    balance = session.scalar(
        select(BalanceORM).where(BalanceORM.user_id == user_id).with_for_update()
    )
    if balance is None:
        raise ValueError("Balance not found")
    if balance.amount < amount:
        raise ValueError("Insufficient balance")

    balance.amount -= amount
    transaction = TransactionORM(
        user_id=user_id,
        request_id=request_id,
        transaction_type="debit",
        amount=amount,
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def create_ml_request(
    session: Session,
    user_id: int,
    model_id: int,
    input_data: list[dict],
    predictions: list,
    invalid_data: list[dict],
) -> MLRequestORM:
    model = session.get(MLModelORM, model_id)
    if model is None:
        raise ValueError("ML model not found")

    charge = model.prediction_cost * len(predictions)
    request = MLRequestORM(
        user_id=user_id,
        model_id=model_id,
        status="completed",
        input_data=input_data,
        predictions=predictions,
        invalid_data=invalid_data,
        charged_credits=charge,
    )
    session.add(request)
    session.flush()

    if charge > 0:
        balance = session.scalar(
            select(BalanceORM).where(BalanceORM.user_id == user_id).with_for_update()
        )
        if balance is None:
            raise ValueError("Balance not found")
        if balance.amount < charge:
            session.rollback()
            raise ValueError("Insufficient balance")

        balance.amount -= charge
        session.add(
            TransactionORM(
                user_id=user_id,
                request_id=request.id,
                transaction_type="debit",
                amount=charge,
            )
        )

    session.commit()
    session.refresh(request)
    return request


def get_transaction_history(session: Session, user_id: int) -> list[TransactionORM]:
    statement = (
        select(TransactionORM)
        .where(TransactionORM.user_id == user_id)
        .order_by(TransactionORM.created_at.desc())
    )
    return list(session.scalars(statement))


def get_request_history(session: Session, user_id: int) -> list[MLRequestORM]:
    statement = (
        select(MLRequestORM)
        .where(MLRequestORM.user_id == user_id)
        .order_by(MLRequestORM.created_at.desc())
    )
    return list(session.scalars(statement))
