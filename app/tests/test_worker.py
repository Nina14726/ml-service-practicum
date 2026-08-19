import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src import worker
from src.database import Base
from src.models import BalanceORM, PredictionTaskORM, TransactionORM
from src.services import create_user


class DummyChannel:
    def __init__(self) -> None:
        self.acked: list[int] = []
        self.nacked: list[tuple[int, bool]] = []

    def basic_ack(self, delivery_tag: int) -> None:
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag: int, requeue: bool) -> None:
        self.nacked.append((delivery_tag, requeue))


@pytest.fixture()
def worker_db(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(worker, "SessionLocal", test_session_local)
    monkeypatch.setattr(worker, "WORKER_ID", "worker-test")
    yield test_session_local
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_queued_task(session_local, model: str) -> tuple[str, int]:
    with session_local() as session:
        user = create_user(
            session,
            email=f"{model}@example.com",
            password_hash="secret",
            initial_balance=Decimal("10.00"),
        )
        user.balance.amount -= Decimal("2.00")
        task = PredictionTaskORM(
            task_id=f"task-{model}",
            user_id=user.id,
            features={"x": 1.5, "y": 2.5},
            model=model,
            charged_credits=Decimal("2.00"),
            status="queued",
            created_at=datetime.now(timezone.utc),
        )
        session.add(task)
        session.add(
            TransactionORM(
                user_id=user.id,
                transaction_type="debit",
                amount=Decimal("2.00"),
            )
        )
        session.commit()
        return task.task_id, user.id


def test_worker_processes_demo_model_successfully(worker_db) -> None:
    task_id, user_id = create_queued_task(worker_db, "demo_model")
    channel = DummyChannel()
    method = SimpleNamespace(delivery_tag=1)
    body = json.dumps(
        {"task_id": task_id, "model": "demo_model", "features": {"x": 1.5, "y": 2.5}}
    ).encode()

    worker.handle_message(channel, method, None, body)

    with worker_db() as session:
        task = session.get(PredictionTaskORM, task_id)
        balance = session.scalar(select(BalanceORM).where(BalanceORM.user_id == user_id))
        assert task is not None
        assert task.status == "success"
        assert task.prediction == 4.0
        assert task.worker_id == "worker-test"
        assert task.error is None
        assert balance is not None
        assert balance.amount == Decimal("8.00")

    assert channel.acked == [1]
    assert channel.nacked == []


def test_worker_failure_refunds_credits(worker_db) -> None:
    task_id, user_id = create_queued_task(worker_db, "unknown-model")
    channel = DummyChannel()
    method = SimpleNamespace(delivery_tag=2)
    body = json.dumps(
        {"task_id": task_id, "model": "unknown-model", "features": {"x": 1.0}}
    ).encode()

    worker.handle_message(channel, method, None, body)

    with worker_db() as session:
        task = session.get(PredictionTaskORM, task_id)
        balance = session.scalar(select(BalanceORM).where(BalanceORM.user_id == user_id))
        transactions = list(
            session.scalars(
                select(TransactionORM)
                .where(TransactionORM.user_id == user_id)
                .order_by(TransactionORM.created_at)
            )
        )
        assert task is not None
        assert task.status == "failed"
        assert task.prediction is None
        assert task.worker_id == "worker-test"
        assert task.error == "unknown model"
        assert balance is not None
        assert balance.amount == Decimal("10.00")
        assert [item.transaction_type for item in transactions] == ["debit", "refund"]
        assert transactions[-1].amount == Decimal("2.00")

    assert channel.acked == [2]
    assert channel.nacked == []
