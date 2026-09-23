import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.observability import ObservabilityMiddleware, configure_logging


def test_request_id_is_preserved_and_returned(client):
    response = client.get("/health", headers={"X-Request-ID": "checkout-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "checkout-123"


def test_invalid_request_id_is_replaced(client):
    response = client.get("/health", headers={"X-Request-ID": "invalid request id"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "invalid request id"
    uuid.UUID(response.headers["X-Request-ID"])


def test_metrics_endpoint_exposes_http_metrics(client):
    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "stock_http_requests_total" in response.text
    assert 'route="/health"' in response.text
    assert "stock_http_request_duration_seconds" in response.text


def test_unhandled_errors_return_safe_correlated_response():
    app = FastAPI()
    app.add_middleware(
        ObservabilityMiddleware,
        logger=configure_logging("CRITICAL"),
    )

    @app.get("/boom")
    def boom():
        raise RuntimeError("sensitive internal detail")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/boom", headers={"X-Request-ID": "error-123"})

    assert response.status_code == 500
    assert response.json() == {
        "detail": "internal_server_error",
        "request_id": "error-123",
    }
    assert response.headers["X-Request-ID"] == "error-123"
    assert "sensitive internal detail" not in response.text


def test_database_errors_return_service_unavailable():
    app = FastAPI()
    app.add_middleware(
        ObservabilityMiddleware,
        logger=configure_logging("CRITICAL"),
    )

    @app.get("/database-error")
    def database_error():
        raise OperationalError("SELECT 1", {}, Exception("database secret"))

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/database-error")

    assert response.status_code == 503
    assert response.json()["detail"] == "database_unavailable"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
