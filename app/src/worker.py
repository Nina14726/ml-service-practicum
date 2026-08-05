import json
import os
from datetime import datetime, timezone

import pika
from sqlalchemy import select

from src.database import SessionLocal, create_tables, wait_for_database
from src.models import BalanceORM, PredictionTaskORM, TransactionORM
from src.rabbitmq import QUEUE_NAME, connect_to_rabbitmq

WORKER_ID = os.getenv("WORKER_ID", "worker-unknown")


def validate_features(features: object) -> dict[str, float]:
    if not isinstance(features, dict) or not features:
        raise ValueError("features must be a non-empty object")

    result: dict[str, float] = {}
    for name, value in features.items():
        if (
            not isinstance(name, str)
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            raise ValueError(
                "all feature names must be strings and values must be numeric"
            )
        result[name] = float(value)
    return result


def predict(features: dict[str, float], model: str) -> float:
    if model != "demo_model":
        raise ValueError("unknown model")
    return sum(features.values())


def save_success(task_id: str, prediction: float) -> None:
    with SessionLocal() as session:
        task = session.get(PredictionTaskORM, task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")
        task.status = "success"
        task.prediction = prediction
        task.worker_id = WORKER_ID
        task.error = None
        task.processed_at = datetime.now(timezone.utc)
        session.commit()


def save_failure_and_refund(task_id: str, error: str) -> None:
    with SessionLocal() as session:
        task = session.scalar(
            select(PredictionTaskORM)
            .where(PredictionTaskORM.task_id == task_id)
            .with_for_update()
        )
        if task is None:
            raise ValueError(f"task {task_id} not found")

        if task.status != "failed" and task.charged_credits > 0:
            balance = session.scalar(
                select(BalanceORM)
                .where(BalanceORM.user_id == task.user_id)
                .with_for_update()
            )
            if balance is None:
                raise ValueError("Balance not found")
            balance.amount += task.charged_credits
            session.add(
                TransactionORM(
                    user_id=task.user_id,
                    transaction_type="refund",
                    amount=task.charged_credits,
                )
            )

        task.status = "failed"
        task.prediction = None
        task.worker_id = WORKER_ID
        task.error = error
        task.processed_at = datetime.now(timezone.utc)
        session.commit()


def handle_message(channel, method, _properties, body: bytes) -> None:
    task_id = "unknown"
    try:
        message = json.loads(body.decode("utf-8"))
        task_id = message["task_id"]
        features = validate_features(message.get("features"))
        model = message.get("model")
        if not isinstance(model, str) or not model:
            raise ValueError("model must be a non-empty string")

        prediction = predict(features, model)
        save_success(task_id, prediction)
        print(
            json.dumps(
                {
                    "task_id": task_id,
                    "prediction": prediction,
                    "worker_id": WORKER_ID,
                    "status": "success",
                }
            )
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as error:
        if task_id == "unknown":
            print(
                json.dumps(
                    {
                        "task_id": task_id,
                        "worker_id": WORKER_ID,
                        "status": "failed",
                        "error": str(error),
                    }
                )
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        try:
            save_failure_and_refund(task_id, str(error))
        except Exception as persistence_error:
            print(
                json.dumps(
                    {
                        "task_id": task_id,
                        "worker_id": WORKER_ID,
                        "status": "requeued",
                        "error": str(persistence_error),
                    }
                )
            )
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        print(
            json.dumps(
                {
                    "task_id": task_id,
                    "worker_id": WORKER_ID,
                    "status": "failed",
                    "error": str(error),
                }
            )
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    wait_for_database()
    create_tables()
    connection = connect_to_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_message)
    print(f"{WORKER_ID} is waiting for messages from {QUEUE_NAME}")
    channel.start_consuming()


if __name__ == "__main__":
    main()
