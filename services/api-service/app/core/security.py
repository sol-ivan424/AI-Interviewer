from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import Settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using the configured modern password hasher."""
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    """Safely compare a password against its stored hash."""
    return password_hash.verify(password, encoded_hash)


def create_access_token(user_id: UUID, settings: Settings) -> str:
    """Create a short-lived JWT access token for one user."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str, settings: Settings) -> UUID | None:
    """Decode a JWT and return its UUID subject, or None for invalid tokens."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        return UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        return None
