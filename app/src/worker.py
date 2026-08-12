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


def video_analysis_result() -> dict:
    return {
        "analysis": {
            "core_idea_dna": {
                "logline": "Короткий визуальный ролик строится вокруг одного понятного действия и удерживает внимание за счёт быстрого развития сцены.",
                "metaphor": "Главный объект работает как визуальный центр истории, а движение подчёркивает переход от ожидания к действию.",
                "target_action": "Заинтересовать зрителя и вызвать желание досмотреть ролик до конца.",
                "strategic_task": "Виральность и удержание внимания.",
            },
            "story_dramaturgy": {
                "genre": "Динамичный короткий визуальный ролик.",
                "hero_arc": "Главный объект проходит от спокойного состояния к активному действию и финальному результату.",
                "structure": {
                    "exposition": "Показывается исходная ситуация и главный объект.",
                    "incident": "Возникает действие, меняющее ритм и направление сцены.",
                    "resolution": "Действие завершается визуальным акцентом.",
                },
                "context_overlay": "Экранный текст должен поддерживать действие и не перекрывать ключевые детали кадра.",
            },
            "sound_design": {
                "music_score": "Средний или быстрый темп, музыка усиливает движение и смену сцен.",
                "sfx": ["шаги или движения героя", "акцент перехода", "атмосферный фон"],
                "the_drop": "Короткое снижение музыки перед главным визуальным акцентом.",
                "sound_bridge": "Звук действия продолжается через монтажную склейку и связывает соседние кадры.",
            },
            "blocking_geometry": {
                "composition": {
                    "foreground": "Ключевой объект или деталь для глубины кадра.",
                    "middleground": "Основное действие.",
                    "background": "Среда, задающая контекст и атмосферу.",
                },
                "movement_vectors": "Движение героя строится по оси Z к камере и дополняется горизонтальным движением по X.",
                "precise_actions": ["приближается", "резко останавливается", "разворачивается", "ускоряется"],
            },
            "cinematography_specs": {
                "camera_state": "Динамичная камера с короткими dolly/pan движениями.",
                "angle": "Преимущественно eye-level с отдельными low-angle акцентами.",
                "optics_lens": "Умеренно широкий угол для ощущения присутствия и пространства.",
                "focus_depth": "Главный объект отделён от фона умеренной глубиной резкости.",
                "fps_speed": "Основной материал в стандартной скорости, акцентные моменты могут использовать slow motion.",
            },
            "art_direction": {
                "palette": "Контрастная палитра с одним доминирующим цветовым акцентом.",
                "visual_rhymes": "Повторяющиеся цвета и формы связывают разные сцены.",
                "lighting": {
                    "source": "Боковой и контровой свет для отделения объекта от фона.",
                    "quality": "Мягкий основной свет с более жёсткими акцентами.",
                },
                "key_props": ["главный объект сцены", "деталь окружения", "визуальный акцент"],
            },
            "editing_psychology": {
                "pacing_tempo": "Короткие кадры в начале и более длинный финальный кадр для фиксации результата.",
                "hooks": {
                    "start_3s": "Сразу показать движение, необычный объект или визуальный конфликт.",
                    "middle_intrigue": "Добавить изменение направления или неожиданный визуальный элемент.",
                    "end_reward": "Завершить ролик ясным результатом или сильным финальным кадром.",
                },
                "diegesis": "Переходы должны сохранять логику пространства и действия.",
                "transitions_matchcuts": "Лучше использовать match-cut по движению, форме или направлению камеры.",
                "emotional_curve": "Интерес → ожидание → ускорение → кульминация → короткое визуальное вознаграждение.",
            },
            "script_breakdown": [
                {
                    "timecode": "0:00–0:03",
                    "action": "Появляется главный объект и сразу начинается действие.",
                    "audio": "Стартовый музыкальный акцент и атмосферный звук.",
                    "meaning": "Hook и постановка исходной ситуации.",
                },
                {
                    "timecode": "0:03–0:10",
                    "action": "Действие развивается, камера следует за объектом и меняет масштаб.",
                    "audio": "Ритм усиливается, добавляются SFX движения.",
                    "meaning": "Развитие интриги и удержание внимания.",
                },
                {
                    "timecode": "0:10–0:15",
                    "action": "Кульминационное действие и финальный визуальный акцент.",
                    "audio": "Короткий drop и финальный удар музыки.",
                    "meaning": "Вознаграждение зрителя и завершение истории.",
                },
            ],
            "analytical_filter": {
                "one_goal_principle": "Ролик должен держаться одной визуальной идеи без лишних параллельных сюжетов.",
                "empathy_effort": "Эмоциональная связь усилится, если усилие героя видно физически, а не только заявлено текстом.",
                "metaphor_logic": "Визуальная причина и следствие должны быть понятны без дополнительного объяснения.",
                "cgi_honesty": "Уровень графики и композитинга должен соответствовать общей стилистике и амбиции ролика.",
                "drop_off_point": "Риск потери внимания появляется, если после первых секунд действие перестаёт развиваться или реклама начинается слишком рано.",
                "unity_of_focus": "В кадре должен оставаться один главный смысловой центр.",
            },
        },
        "reproduction_prompt": "Create a cinematic short-form video with a clear single visual idea. Open with immediate action in the first three seconds, keep one main subject as the visual focus, use dynamic eye-level and occasional low-angle shots, moderate wide-angle optics, shallow-to-medium depth of field, lateral and forward camera movement, strong foreground/midground/background separation, directional side and rim lighting, a controlled contrast palette, rhythmic cuts with motion match-cuts, tactile sound effects, a short music drop before the climax, and a strong final visual reward. Preserve spatial logic and make every action precise, readable and physically motivated.",
    }


def predict(features: dict[str, float], model: str) -> tuple[float | None, dict | None]:
    if model == "demo_model":
        return sum(features.values()), None
    if model == "video_analysis":
        return None, video_analysis_result()
    raise ValueError("unknown model")


def save_success(
    task_id: str,
    prediction: float | None,
    result: dict | None,
) -> None:
    with SessionLocal() as session:
        task = session.get(PredictionTaskORM, task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")
        task.status = "success"
        task.prediction = prediction
        task.result = result
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
        task.result = None
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

        prediction, result = predict(features, model)
        save_success(task_id, prediction, result)
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
