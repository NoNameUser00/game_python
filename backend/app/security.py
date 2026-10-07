"""Пароли и JWT."""
from datetime import datetime, timedelta, timezone

import jwt

from .config import JWT_ALGORITHM, JWT_EXPIRE_DAYS, JWT_SECRET


def hash_password(password: str) -> str:
    # PBKDF2 из стандартной библиотеки — без лишних зависимостей.
    import hashlib
    import secrets

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    import hashlib

    try:
        _, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return secrets_compare(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def secrets_compare(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a, b)


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
