from __future__ import annotations

import pytest

from app.config import Settings


def _production_settings(**overrides):
    values = {
        "APP_ENV": "production",
        "POSTGRES_PASSWORD": "strong-postgres-password",
        "MINIO_ACCESS_KEY": "strong-minio-user",
        "MINIO_SECRET_KEY": "strong-minio-password",
        "JWT_SECRET_KEY": "x" * 64,
        "JWT_REFRESH_SECRET_KEY": "y" * 64,
        "ENCRYPTION_KEY": "a" * 64,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        _production_settings(JWT_SECRET_KEY="replace-me-with-a-secure-random-secret")


def test_production_rejects_invalid_encryption_key():
    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        _production_settings(ENCRYPTION_KEY="not-hex")


def test_production_accepts_strong_required_secrets():
    settings = _production_settings()

    assert settings.APP_ENV == "production"
