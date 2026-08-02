import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://ml_user:ml_password@database:5432/ml_service",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def wait_for_database(attempts: int = 10, delay: float = 2.0) -> None:
    """Wait until PostgreSQL accepts connections."""
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as error:
            last_error = error
            time.sleep(delay)

    raise RuntimeError("Database is unavailable") from last_error


def create_tables() -> None:
    from src import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
