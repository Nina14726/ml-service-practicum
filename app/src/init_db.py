from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import SessionLocal, create_tables, wait_for_database
from src.models import BalanceORM, MLModelORM, UserORM


def initialize_demo_data(session: Session) -> None:
    demo_users = [
        {
            "email": "demo@example.com",
            "password_hash": "demo_password_hash",
            "role": "user",
            "balance": Decimal("100.00"),
        },
        {
            "email": "admin@example.com",
            "password_hash": "admin_password_hash",
            "role": "admin",
            "balance": Decimal("500.00"),
        },
    ]

    for data in demo_users:
        user = session.scalar(select(UserORM).where(UserORM.email == data["email"]))
        if user is None:
            user = UserORM(
                email=data["email"],
                password_hash=data["password_hash"],
                role=data["role"],
            )
            user.balance = BalanceORM(amount=data["balance"])
            session.add(user)

    demo_models = [
        {
            "name": "binary-classifier",
            "description": "Demo binary classification model",
            "prediction_cost": Decimal("2.00"),
        },
        {
            "name": "regression-model",
            "description": "Demo regression model",
            "prediction_cost": Decimal("3.00"),
        },
    ]

    for data in demo_models:
        model = session.scalar(
            select(MLModelORM).where(MLModelORM.name == data["name"])
        )
        if model is None:
            session.add(MLModelORM(**data))

    session.commit()


def init_database() -> None:
    wait_for_database()
    create_tables()
    with SessionLocal() as session:
        initialize_demo_data(session)


if __name__ == "__main__":
    init_database()
