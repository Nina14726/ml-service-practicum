import json
import os
from datetime import datetime, timezone

import pika

from src.database import SessionLocal, create_tables, wait_for_database
from src.models import PredictionTaskORM
from src.rabbitmq import QUEUE_NAME, connect_to_rabbitmq

WORKER_ID = os.getenv("WORKER_ID", "worker-unknown")


def validate_features(features: object) -> dict[str, float]:
    if not isinstance(features, dict) or not features:
        raise ValueError("features must be a non-empty object")

    result: dict[str, float] = {}
    for name, value in features.items():
        if not isinstance(name, str) or not isinstance(value, (int, float)):
            raise ValueError("all feature names must be strings and values must be numeric")
        result[name] = float(value)
    return result


def predict(features: dict[str, float], model: str) -> float:
    if model != "demo_model":
        raise ValueError("unknown model")
    return sum(features.values())


def save_result(task_id: str, status: str, prediction: float | None = None, error: str | None = None) -> None:
    with SessionLocal() as session:
        task = session.get(PredictionTaskORM, task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")
        task.status = status
        task.prediction = prediction
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
        save_result(task_id, "success", prediction=prediction)
        print(json.dumps({"task_id": task_id, "prediction": prediction, "worker_id": WORKER_ID, "status": "success"}))
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as error:
        if task_id != "unknown":
            try:
                save_result(task_id, "failed", error=str(error))
            except Exception:
                pass
        print(json.dumps({"task_id": task_id, "worker_id": WORKER_ID, "status": "failed", "error": str(error)}))
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
