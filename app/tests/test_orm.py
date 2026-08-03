from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.init_db import initialize_demo_data
from src.models import BalanceORM, MLModelORM, MLRequestORM, TransactionORM, UserORM
from src.services import (
    create_ml_request,
    create_user,
    debit_balance,
    get_request_history,
    get_transaction_history,
    get_user_by_email,
    top_up_balance,
)


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db_session:
        yield db_session


def test_user_balance_transactions_and_request_history(session: Session) -> None:
    user = create_user(
        session,
        email="student@example.com",
        password_hash="hash",
        initial_balance=Decimal("20.00"),
    )
    loaded_user = get_user_by_email(session, user.email)
    assert loaded_user is not None
    assert loaded_user.balance.amount == Decimal("20.00")

    top_up_balance(session, user.id, Decimal("10.00"))
    balance = session.scalar(select(BalanceORM).where(BalanceORM.user_id == user.id))
    assert balance is not None
    assert balance.amount == Decimal("30.00")

    model = MLModelORM(
        name="test-model",
        description="Test model",
        prediction_cost=Decimal("2.00"),
    )
    session.add(model)
    session.commit()

    request = create_ml_request(
        session,
        user_id=user.id,
        model_id=model.id,
        input_data=[{"value": 1}, {"value": 2}, {"value": "error"}],
        predictions=[0, 1],
        invalid_data=[{"value": "error"}],
    )

    session.refresh(balance)
    transactions = get_transaction_history(session, user.id)
    requests = get_request_history(session, user.id)

    assert balance.amount == Decimal("26.00")
    assert request.charged_credits == Decimal("4.00")
    assert request.model.id == model.id
    assert request.invalid_data == [{"value": "error"}]

    assert len(transactions) == 2
    assert {transaction.transaction_type for transaction in transactions} == {
        "credit",
        "debit",
    }
    debit_transaction = next(
        transaction
        for transaction in transactions
        if transaction.transaction_type == "debit"
    )
    assert debit_transaction.amount == Decimal("4.00")
    assert debit_transaction.request_id == request.id
    assert debit_transaction.request.id == request.id

    assert len(requests) == 1
    assert requests[0].id == request.id


def test_direct_debit_balance(session: Session) -> None:
    user = create_user(
        session,
        email="debit@example.com",
        password_hash="hash",
        initial_balance=Decimal("15.00"),
    )

    transaction = debit_balance(session, user.id, Decimal("5.00"))
    balance = session.scalar(select(BalanceORM).where(BalanceORM.user_id == user.id))

    assert balance is not None
    assert balance.amount == Decimal("10.00")
    assert transaction.transaction_type == "debit"
    assert transaction.amount == Decimal("5.00")


def test_insufficient_balance_rolls_back_request(session: Session) -> None:
    user = create_user(
        session,
        email="poor@example.com",
        password_hash="hash",
        initial_balance=Decimal("1.00"),
    )
    model = MLModelORM(
        name="expensive-model",
        description="Expensive model",
        prediction_cost=Decimal("5.00"),
    )
    session.add(model)
    session.commit()

    with pytest.raises(ValueError, match="Insufficient balance"):
        create_ml_request(
            session,
            user_id=user.id,
            model_id=model.id,
            input_data=[{"value": 1}],
            predictions=[1],
            invalid_data=[],
        )

    assert get_request_history(session, user.id) == []
    assert session.scalar(select(TransactionORM)) is None


def test_request_history_is_sorted_by_date(session: Session) -> None:
    user = create_user(
        session,
        email="history@example.com",
        password_hash="hash",
        initial_balance=Decimal("20.00"),
    )
    model = MLModelORM(
        name="history-model",
        description="History model",
        prediction_cost=Decimal("1.00"),
    )
    session.add(model)
    session.commit()

    older_request = create_ml_request(
        session,
        user_id=user.id,
        model_id=model.id,
        input_data=[{"value": 1}],
        predictions=[1],
        invalid_data=[],
    )
    newer_request = create_ml_request(
        session,
        user_id=user.id,
        model_id=model.id,
        input_data=[{"value": 2}],
        predictions=[0],
        invalid_data=[],
    )

    older_request.created_at = datetime.now(timezone.utc) - timedelta(days=1)
    newer_request.created_at = datetime.now(timezone.utc)
    session.commit()

    history = get_request_history(session, user.id)

    assert [request.id for request in history] == [newer_request.id, older_request.id]


def test_demo_initialization_is_idempotent(session: Session) -> None:
    initialize_demo_data(session)
    initialize_demo_data(session)

    users = list(session.scalars(select(UserORM)))
    models = list(session.scalars(select(MLModelORM)))

    assert len(users) == 2
    assert len(models) == 2
    assert {user.role for user in users} == {"user", "admin"}
    assert all(user.balance is not None for user in users)
