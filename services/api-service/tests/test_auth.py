import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.models  # noqa: F401
from app.core.config import Settings
from app.core.security import verify_password
from app.db.base import Base
from app.main import create_app
from app.models.user import User


@pytest.fixture
def auth_app(tmp_path: Path) -> FastAPI:
    database_path = (tmp_path / "auth.sqlite3").as_posix()
    settings = Settings(
        app_name="Test API",
        app_env="test",
        app_version="0.0.0-test",
        debug=False,
        database_url=f"sqlite+aiosqlite:///{database_path}",
        jwt_secret_key="test-secret-key-that-is-long-enough",
        access_token_expire_minutes=5,
        cors_origins="http://localhost:3000",
    )
    application = create_app(settings)

    async def create_schema() -> None:
        async with application.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    return application


def register_user(client: TestClient, email: str = "user@example.com"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
            "full_name": "Иван Иванов",
        },
    )


def test_register_login_and_get_current_user(auth_app: FastAPI) -> None:
    with TestClient(auth_app) as client:
        registration = register_user(client)
        assert registration.status_code == 201
        assert registration.json()["email"] == "user@example.com"
        assert registration.json()["full_name"] == "Иван Иванов"
        assert "password" not in registration.json()
        assert "password_hash" not in registration.json()

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "USER@example.com", "password": "StrongPassword123"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        assert login.json()["token_type"] == "bearer"

        me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["id"] == registration.json()["id"]
        assert me.json()["email"] == "user@example.com"
        assert "password_hash" not in me.json()


def test_duplicate_email_is_case_insensitive(auth_app: FastAPI) -> None:
    with TestClient(auth_app) as client:
        assert register_user(client, "User@Example.com").status_code == 201
        duplicate = register_user(client, "user@example.com")

    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "A user with this email already exists"}


def test_short_password_is_rejected(auth_app: FastAPI) -> None:
    with TestClient(auth_app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "short", "full_name": None},
        )

    assert response.status_code == 422


def test_invalid_login_uses_generic_unauthorized_response(auth_app: FastAPI) -> None:
    with TestClient(auth_app) as client:
        register_user(client)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "WrongPassword123"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_me_requires_valid_bearer_token(auth_app: FastAPI) -> None:
    with TestClient(auth_app) as client:
        missing = client.get("/api/v1/users/me")
        invalid = client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer not-a-valid-token"}
        )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"


def test_password_is_hashed_in_database(auth_app: FastAPI) -> None:
    with TestClient(auth_app) as client:
        register_user(client)

        async def load_user() -> User:
            async with auth_app.state.session_factory() as session:
                result = await session.execute(select(User).where(User.email == "user@example.com"))
                return result.scalar_one()

        user = asyncio.run(load_user())

    assert user.password_hash != "StrongPassword123"
    assert verify_password("StrongPassword123", user.password_hash)


def test_auth_secrets_are_not_logged(auth_app: FastAPI, caplog) -> None:
    password = "LogSecretPassword123"
    with TestClient(auth_app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "logs@example.com", "password": password, "full_name": "Logs"},
        )
        assert registration.status_code == 201
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "logs@example.com", "password": password},
        )
        assert login.status_code == 200

    assert password not in caplog.text
    assert login.json()["access_token"] not in caplog.text
    assert "password_hash" not in caplog.text
