import time

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy import func, select

from src.database import SessionLocal
from src.models import MLRequestORM, PredictionTaskORM, TransactionORM, UserORM

router = APIRouter()

HTTP_REQUESTS = Counter(
    "ml_service_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "ml_service_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)
HTTP_REQUESTS_ACTIVE = Gauge(
    "ml_service_http_requests_active",
    "Currently active HTTP requests",
)
USERS_TOTAL = Gauge("ml_service_users_total", "Registered users")
ML_REQUESTS_TOTAL = Gauge("ml_service_ml_requests_total", "Stored synchronous ML requests")
PREDICTION_TASKS_TOTAL = Gauge(
    "ml_service_prediction_tasks_total",
    "Asynchronous prediction tasks",
    ["status"],
)
TRANSACTIONS_TOTAL = Gauge(
    "ml_service_transactions_total",
    "Balance transactions",
    ["type"],
)


def _path_label(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path or request.url.path


async def metrics_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    started = time.perf_counter()
    HTTP_REQUESTS_ACTIVE.inc()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        path = _path_label(request)
        HTTP_REQUESTS.labels(request.method, path, str(status_code)).inc()
        HTTP_REQUEST_DURATION.labels(request.method, path).observe(
            time.perf_counter() - started
        )
        HTTP_REQUESTS_ACTIVE.dec()


def refresh_business_metrics() -> None:
    with SessionLocal() as session:
        USERS_TOTAL.set(session.scalar(select(func.count()).select_from(UserORM)) or 0)
        ML_REQUESTS_TOTAL.set(
            session.scalar(select(func.count()).select_from(MLRequestORM)) or 0
        )

        for status in ("queued", "success", "failed"):
            count = session.scalar(
                select(func.count())
                .select_from(PredictionTaskORM)
                .where(PredictionTaskORM.status == status)
            )
            PREDICTION_TASKS_TOTAL.labels(status).set(count or 0)

        transaction_types = session.execute(
            select(TransactionORM.transaction_type, func.count())
            .group_by(TransactionORM.transaction_type)
        ).all()
        known_types = {"credit", "debit", "refund"}
        values = {name: count for name, count in transaction_types}
        for transaction_type in known_types | set(values):
            TRANSACTIONS_TOTAL.labels(transaction_type).set(
                values.get(transaction_type, 0)
            )


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    refresh_business_metrics()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
