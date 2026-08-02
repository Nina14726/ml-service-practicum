from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.init_db import init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="ML Service", lifespan=lifespan)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "ML service is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
