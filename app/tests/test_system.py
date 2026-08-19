from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.dependencies import TOKENS, get_session
from src.database import Base
from src.main import app
from src.models import MLModelORM


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        sync_model = MLModelORM(
            name="sync-test-model",
            description="Model for API tests",
            prediction_cost=Decimal("2.00"),
        )
        async_model = MLModelORM(
            name="demo_model",
            description="RabbitMQ demo model",
            prediction_cost=Decimal("2.00"),
        )
        session.add_all([sync_model, async_model])
        session.commit()
        sync_model_id = sync_model.id

    def override_session():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    published: list[dict] = []

    def fake_publish(message: dict) -> None:
        published.append(message)

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr("src.api.tasks.publish_task", fake_publish)
    TOKENS.clear()

    test_client = TestClient(app)
    yield test_client, sync_model_id, published

    test_client.close()
    app.dependency_overrides.clear()
    TOKENS.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register_and_login(client: TestClient, email: str = "student@example.com") -> dict[str, str]:
    register = client.post(
        "/auth/register",
        json={"email": email, "password": "secret123"},
    )
    assert register.status_code == 201

    login = client.post(
        "/auth/login",
        json={"email": email, "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def amount(response) -> Decimal:
    return Decimal(str(response.json()["amount"]))


def test_user_registration_login_repeat_login_and_errors(client) -> None:
    test_client, _, _ = client

    created = test_client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert created.status_code == 201
    assert created.json()["email"] == "user@example.com"

    duplicate = test_client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert duplicate.status_code == 409

    first_login = test_client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "secret123"},
    )
    second_login = test_client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert first_login.status_code == 200
    assert second_login.status_code == 200
    assert first_login.json()["access_token"]
    assert second_login.json()["access_token"]

    wrong_password = test_client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "wrong"},
    )
    assert wrong_password.status_code == 401

    no_token = test_client.get("/balance")
    assert no_token.status_code == 401


def test_balance_top_up_and_updated_value(client) -> None:
    test_client, _, _ = client
    headers = register_and_login(test_client)

    initial = test_client.get("/balance", headers=headers)
    assert initial.status_code == 200
    assert amount(initial) == Decimal("0.00")

    topped_up = test_client.post(
        "/balance/top-up",
        headers=headers,
        json={"amount": "10.00"},
    )
    assert topped_up.status_code == 200
    assert amount(topped_up) == Decimal("10.00")

    current = test_client.get("/balance", headers=headers)
    assert current.status_code == 200
    assert amount(current) == Decimal("10.00")


def test_successful_prediction_charges_balance_and_saves_history(client) -> None:
    test_client, model_id, _ = client
    headers = register_and_login(test_client)
    test_client.post("/balance/top-up", headers=headers, json={"amount": "10.00"})

    prediction = test_client.post(
        "/predict/sync",
        headers=headers,
        json={
            "model_id": model_id,
            "data": [{"value": 0.2}, {"value": 0.8}],
        },
    )
    assert prediction.status_code == 200
    body = prediction.json()
    assert body["predictions"] == [0, 1]
    assert Decimal(str(body["charged_credits"])) == Decimal("4.00")

    balance = test_client.get("/balance", headers=headers)
    assert amount(balance) == Decimal("6.00")

    request_history = test_client.get("/history/requests", headers=headers)
    assert request_history.status_code == 200
    assert len(request_history.json()) == 1
    assert request_history.json()[0]["id"] == body["request_id"]

    transaction_history = test_client.get("/history/transactions", headers=headers)
    assert transaction_history.status_code == 200
    transactions = transaction_history.json()
    assert {item["transaction_type"] for item in transactions} == {"credit", "debit"}
    debit = next(item for item in transactions if item["transaction_type"] == "debit")
    assert Decimal(str(debit["amount"])) == Decimal("4.00")
    assert debit["request_id"] == body["request_id"]


def test_insufficient_balance_does_not_create_request_or_debit(client) -> None:
    test_client, model_id, _ = client
    headers = register_and_login(test_client)
    test_client.post("/balance/top-up", headers=headers, json={"amount": "1.00"})

    prediction = test_client.post(
        "/predict/sync",
        headers=headers,
        json={"model_id": model_id, "data": [{"value": 1}]},
    )
    assert prediction.status_code == 402

    balance = test_client.get("/balance", headers=headers)
    assert amount(balance) == Decimal("1.00")

    requests = test_client.get("/history/requests", headers=headers).json()
    assert requests == []

    transactions = test_client.get("/history/transactions", headers=headers).json()
    assert [item["transaction_type"] for item in transactions] == ["credit"]


def test_invalid_prediction_data_does_not_charge_balance(client) -> None:
    test_client, model_id, _ = client
    headers = register_and_login(test_client)
    test_client.post("/balance/top-up", headers=headers, json={"amount": "10.00"})

    prediction = test_client.post(
        "/predict/sync",
        headers=headers,
        json={"model_id": model_id, "data": [{"value": "bad"}]},
    )
    assert prediction.status_code == 400
    assert prediction.json()["detail"] == "No valid rows for prediction"

    balance = test_client.get("/balance", headers=headers)
    assert amount(balance) == Decimal("10.00")

    requests = test_client.get("/history/requests", headers=headers).json()
    assert requests == []


def test_partially_valid_prediction_charges_only_valid_rows(client) -> None:
    test_client, model_id, _ = client
    headers = register_and_login(test_client)
    test_client.post("/balance/top-up", headers=headers, json={"amount": "10.00"})

    prediction = test_client.post(
        "/predict/sync",
        headers=headers,
        json={
            "model_id": model_id,
            "data": [{"value": 0.9}, {"value": "bad"}],
        },
    )
    assert prediction.status_code == 200
    body = prediction.json()
    assert body["predictions"] == [1]
    assert body["invalid_data"] == [{"value": "bad"}]
    assert Decimal(str(body["charged_credits"])) == Decimal("2.00")

    balance = test_client.get("/balance", headers=headers)
    assert amount(balance) == Decimal("8.00")


def test_async_request_is_published_and_visible_in_task_history(client) -> None:
    test_client, _, published = client
    headers = register_and_login(test_client)
    test_client.post("/balance/top-up", headers=headers, json={"amount": "10.00"})

    response = test_client.post(
        "/predict",
        headers=headers,
        json={"model": "demo_model", "features": {"x": 1.5, "y": 2.5}},
    )
    assert response.status_code == 202
    task_id = response.json()["task_id"]
    assert response.json()["status"] == "queued"

    assert len(published) == 1
    assert published[0]["task_id"] == task_id
    assert published[0]["model"] == "demo_model"
    assert published[0]["features"] == {"x": 1.5, "y": 2.5}

    result = test_client.get(f"/predict/{task_id}", headers=headers)
    assert result.status_code == 200
    assert result.json()["status"] == "queued"
    assert Decimal(str(result.json()["charged_credits"])) == Decimal("2.00")

    task_history = test_client.get("/web/api/tasks", headers=headers)
    assert task_history.status_code == 200
    assert task_history.json()[0]["task_id"] == task_id

    balance = test_client.get("/balance", headers=headers)
    assert amount(balance) == Decimal("8.00")
