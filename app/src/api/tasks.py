from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import BalanceORM, MLModelORM, PredictionTaskORM, TransactionORM, UserORM
from src.rabbitmq import publish_task
from src.schemas import AsyncPredictionAccepted


def enqueue_task(*, session: Session, user: UserORM, model_name: str, features: dict, source_name: str | None = None, source_size: int | None = None, source_duration: float | None = None) -> AsyncPredictionAccepted:
    model = session.scalar(select(MLModelORM).where(MLModelORM.name == model_name))
    if model is None:
        raise HTTPException(status_code=404, detail="ML model not found")
    balance = session.scalar(select(BalanceORM).where(BalanceORM.user_id == user.id).with_for_update())
    if balance is None:
        raise HTTPException(status_code=404, detail="Balance not found")
    if balance.amount < model.prediction_cost:
        raise HTTPException(status_code=402, detail="Insufficient balance")

    task_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    balance.amount -= model.prediction_cost
    task = PredictionTaskORM(task_id=task_id, user_id=user.id, features=features, model=model_name, charged_credits=model.prediction_cost, source_name=source_name, source_size=source_size, source_duration=source_duration, status="queued", created_at=created_at)
    session.add(task)
    session.add(TransactionORM(user_id=user.id, transaction_type="debit", amount=model.prediction_cost))
    session.commit()

    try:
        publish_task({"task_id": task_id, "features": features, "model": model_name, "timestamp": created_at.isoformat()})
    except Exception as error:
        balance = session.scalar(select(BalanceORM).where(BalanceORM.user_id == user.id).with_for_update())
        if balance is not None:
            balance.amount += model.prediction_cost
            session.add(TransactionORM(user_id=user.id, transaction_type="refund", amount=model.prediction_cost))
        task.status = "failed"
        task.error = f"publish error: {error}"
        task.processed_at = datetime.now(timezone.utc)
        session.commit()
        raise HTTPException(status_code=503, detail="RabbitMQ is unavailable") from error
    return AsyncPredictionAccepted(task_id=task_id, status="queued")
