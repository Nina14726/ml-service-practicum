from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from src.api.auth import router as auth_router
from src.api.balance import router as balance_router
from src.api.history import router as history_router
from src.api.predictions import router as predictions_router
from src.init_db import init_database
from src.logging_config import configure_logging
from src.monitoring import metrics_middleware, router as monitoring_router
from src.web import router as web_router

configure_logging()
logger = logging.getLogger("ml-service")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    logger.info("service_started")
    yield
    logger.info("service_stopped")


app = FastAPI(title="ML Service", lifespan=lifespan)
app.middleware("http")(metrics_middleware)
app.include_router(auth_router)
app.include_router(balance_router)
app.include_router(predictions_router)
app.include_router(history_router)
app.include_router(web_router)
app.include_router(monitoring_router)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed method=%s path=%s", request.method, request.url.path)
        raise
    logger.info(
        "request method=%s path=%s status=%s",
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/web")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
