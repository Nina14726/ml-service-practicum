import json
import os
import time
from typing import Any

import pika

QUEUE_NAME = os.getenv("RABBITMQ_QUEUE", "ml_tasks")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))


def connect_to_rabbitmq(attempts: int = 15, delay: float = 2.0) -> pika.BlockingConnection:
    last_error: Exception | None = None
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        heartbeat=60,
        blocked_connection_timeout=30,
    )

    for _ in range(attempts):
        try:
            return pika.BlockingConnection(parameters)
        except pika.exceptions.AMQPError as error:
            last_error = error
            time.sleep(delay)

    raise RuntimeError("RabbitMQ is unavailable") from last_error


def publish_task(message: dict[str, Any]) -> None:
    connection = connect_to_rabbitmq()
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(message).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
    finally:
        connection.close()
