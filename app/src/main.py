from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.api.auth import router as auth_router
from src.api.balance import router as balance_router
from src.api.history import router as history_router
from src.api.predictions import router as predictions_router
from src.init_db import init_database
from src.web import router as web_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="ML Service", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(balance_router)
app.include_router(predictions_router)
app.include_router(history_router)
app.include_router(web_router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/web")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
