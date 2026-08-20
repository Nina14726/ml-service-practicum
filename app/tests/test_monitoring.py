from fastapi import FastAPI
from fastapi.testclient import TestClient

from src import monitoring


def test_metrics_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(monitoring, "refresh_business_metrics", lambda: None)
    app = FastAPI()
    app.include_router(monitoring.router)

    response = TestClient(app).get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "ml_service_http_requests_total" in response.text
    assert "ml_service_users_total" in response.text


def test_http_middleware_records_request() -> None:
    app = FastAPI()
    app.middleware("http")(monitoring.metrics_middleware)

    @app.get("/example")
    def example():
        return {"ok": True}

    client = TestClient(app)
    before = monitoring.HTTP_REQUESTS.labels("GET", "/example", "200")._value.get()
    response = client.get("/example")
    after = monitoring.HTTP_REQUESTS.labels("GET", "/example", "200")._value.get()

    assert response.status_code == 200
    assert after == before + 1
