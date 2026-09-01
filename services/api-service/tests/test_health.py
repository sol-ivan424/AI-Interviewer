from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_returns_service_metadata() -> None:
    settings = Settings(
        app_name="Test API",
        app_env="test",
        app_version="0.0.0-test",
        debug=False,
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret_key="test-secret-key-that-is-long-enough",
        cors_origins="http://localhost:3000",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Test API",
        "version": "0.0.0-test",
        "environment": "test",
    }


def test_cors_origins_are_configurable() -> None:
    settings = Settings(
        app_name="Test API",
        app_env="test",
        app_version="0.0.0-test",
        debug=False,
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret_key="test-secret-key-that-is-long-enough",
        cors_origins="https://allowed.example, https://second.example",
    )
    headers = {
        "Access-Control-Request-Method": "GET",
        "Origin": "https://allowed.example",
    }

    with TestClient(create_app(settings)) as client:
        allowed = client.options("/health", headers=headers)
        denied = client.options("/health", headers={**headers, "Origin": "https://denied.example"})

    assert allowed.headers["access-control-allow-origin"] == "https://allowed.example"
    assert "access-control-allow-origin" not in denied.headers
