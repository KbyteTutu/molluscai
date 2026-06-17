from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import JWTError, jwt

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)


def _exp_to_datetime(payload: dict) -> datetime:
    return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)


class TestHashPassword:
    def test_returns_non_empty_string(self) -> None:
        hashed = hash_password("secret-password")

        assert isinstance(hashed, str)
        assert hashed

    def test_different_passwords_yield_different_hashes(self) -> None:
        first = hash_password("password-one")
        second = hash_password("password-two")

        assert first != second

    def test_same_password_yields_different_hashes_due_to_salt(self) -> None:
        first = hash_password("same-password")
        second = hash_password("same-password")

        assert first != second
        assert verify_password("same-password", first) is True
        assert verify_password("same-password", second) is True

    def test_handles_unicode_passwords(self) -> None:
        password = "pässwörd🔐海螺"
        hashed = hash_password(password)

        assert hashed
        assert verify_password(password, hashed) is True

    def test_handles_max_length_passwords(self) -> None:
        password = "x" * 10_000
        hashed = hash_password(password)

        assert hashed
        assert verify_password(password, hashed) is True


class TestVerifyPassword:
    def test_correct_password_returns_true(self) -> None:
        hashed = hash_password("correct-password")

        assert verify_password("correct-password", hashed) is True

    def test_wrong_password_returns_false(self) -> None:
        hashed = hash_password("correct-password")

        assert verify_password("wrong-password", hashed) is False

    def test_handles_empty_string(self) -> None:
        hashed = hash_password("")

        assert verify_password("", hashed) is True
        assert verify_password("not-empty", hashed) is False


class TestCreateAccessToken:
    def test_returns_non_empty_string(self) -> None:
        token = create_access_token(subject="user-123")

        assert isinstance(token, str)
        assert token

    def test_contains_expected_claims(self) -> None:
        token = create_access_token(subject="user-123")
        payload = verify_token(token, token_type="access")

        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_respects_custom_expires_delta(self) -> None:
        before = datetime.now(timezone.utc)
        token = create_access_token(
            subject="user-123",
            expires_delta=timedelta(minutes=5),
        )
        after = datetime.now(timezone.utc)
        payload = verify_token(token, token_type="access")
        expires_at = _exp_to_datetime(payload)

        assert before + timedelta(minutes=5, seconds=-1) <= expires_at
        assert expires_at <= after + timedelta(minutes=5)

    def test_merges_extra_claims(self) -> None:
        token = create_access_token(
            subject="user-123",
            extra_claims={"role": "admin", "scope": ["read", "write"]},
        )
        payload = verify_token(token, token_type="access")

        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert payload["role"] == "admin"
        assert payload["scope"] == ["read", "write"]


class TestCreateRefreshToken:
    def test_returns_non_empty_string(self) -> None:
        token = create_refresh_token(subject="user-456")

        assert isinstance(token, str)
        assert token

    def test_contains_expected_claims(self) -> None:
        token = create_refresh_token(subject="user-456")
        payload = verify_token(token, token_type="refresh")

        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_respects_custom_expires_delta(self) -> None:
        before = datetime.now(timezone.utc)
        token = create_refresh_token(
            subject="user-456",
            expires_delta=timedelta(days=2),
        )
        after = datetime.now(timezone.utc)
        payload = verify_token(token, token_type="refresh")
        expires_at = _exp_to_datetime(payload)

        assert before + timedelta(days=2, seconds=-1) <= expires_at
        assert expires_at <= after + timedelta(days=2)


class TestVerifyToken:
    def test_valid_token_returns_payload_dict(self) -> None:
        token = create_access_token(subject="user-123", extra_claims={"role": "member"})

        payload = verify_token(token, token_type="access")

        assert isinstance(payload, dict)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert payload["role"] == "member"

    def test_expired_token_raises_jwt_error(self) -> None:
        token = create_access_token(
            subject="user-123",
            expires_delta=timedelta(seconds=-1),
        )

        with pytest.raises(JWTError):
            verify_token(token, token_type="access")

    def test_wrong_secret_raises_jwt_error(self) -> None:
        token = create_access_token(subject="user-123")

        with patch.object(settings, "JWT_SECRET_KEY", "wrong-secret"):
            with pytest.raises(JWTError):
                verify_token(token, token_type="access")

    def test_wrong_token_type_raises_jwt_error(self) -> None:
        token = jwt.encode(
            {
                "sub": "user-123",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
                "type": "refresh",
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        with pytest.raises(JWTError, match="Invalid token type"):
            verify_token(token, token_type="access")

    def test_malformed_token_raises_jwt_error(self) -> None:
        with pytest.raises(JWTError):
            verify_token("not-a-valid-token", token_type="access")
