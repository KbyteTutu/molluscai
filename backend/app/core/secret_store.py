from __future__ import annotations

import base64
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


SECRET_PREFIX = "fernet:"


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    raw_key = bytes.fromhex(settings.ENCRYPTION_KEY)
    return Fernet(base64.urlsafe_b64encode(raw_key))


def encrypt_secret(value: str) -> str:
    if not value:
        return value
    if value.startswith(SECRET_PREFIX):
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{SECRET_PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    if not value or not value.startswith(SECRET_PREFIX):
        return value
    token = value[len(SECRET_PREFIX):]
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise ValueError("Invalid encrypted secret") from exc


def secret_tail(value: str, length: int = 4) -> str | None:
    plain = decrypt_secret(value or "")
    return f"...{plain[-length:]}" if len(plain) >= length else None
