"""Shared test fixtures and configuration for MolluscAI backend tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Generator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ────────────────────────────────────────────────────────────
# Test config override
# ────────────────────────────────────────────────────────────
settings.JWT_SECRET_KEY = "test-secret-key-not-random"
settings.JWT_REFRESH_SECRET_KEY = "test-refresh-secret-key-not-random"
settings.ENCRYPTION_KEY = "a" * 64
settings.DEBUG = True


# ────────────────────────────────────────────────────────────
# Mock database session
# ────────────────────────────────────────────────────────────
class MockResult:
    """Simulates SQLAlchemy Result for scalar/row returns."""

    def __init__(self, rows: list[Any] | None = None, scalar_val: Any = None):
        self._rows = rows or []
        self._scalar_val = scalar_val
        self._iter_idx = 0

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        return self._scalar_val

    def scalar_one(self):
        if self._scalar_val is None:
            raise ValueError("No result")
        return self._scalar_val

    def __iter__(self):
        return iter(self._rows)

    def __next__(self):
        if self._iter_idx >= len(self._rows):
            raise StopIteration
        val = self._rows[self._iter_idx]
        self._iter_idx += 1
        return val


class MockRow:
    """Simulates a SQLAlchemy Row with attribute and mapping access."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self._mapping = kwargs

    def __getitem__(self, key):
        return self._mapping[key]

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._mapping.get(name)


@pytest.fixture
def mock_db() -> AsyncMock:
    """Return an AsyncMock simulating an SQLAlchemy AsyncSession."""
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.begin = AsyncMock()
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock()
    return session


# ────────────────────────────────────────────────────────────
# Test user fixtures
# ────────────────────────────────────────────────────────────
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000999")


def _make_test_user(
    user_id: uuid.UUID = TEST_USER_ID,
    username: str = "testuser",
    email: str = "test@example.com",
    role: str = "user",
    is_active: bool = True,
):
    """Create a mock User object for testing."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = email
    user.role = role
    user.is_active = is_active
    user.password_hash = (
        "$2b$12$LJ3m4ys3Lc.4xVqVFCbjoO2SOq3KqYJqGqX3KqYJqGqX3KqYJqGqX"
    )
    return user


def make_test_user(
    user_id: uuid.UUID = TEST_USER_ID,
    username: str = "testuser",
    email: str = "test@example.com",
    role: str = "user",
    is_active: bool = True,
):
    """Public helper for creating test users in service tests."""
    return _make_test_user(
        user_id=user_id,
        username=username,
        email=email,
        role=role,
        is_active=is_active,
    )


@pytest.fixture
def test_user():
    """Standard test user with 'user' role."""
    return _make_test_user()


@pytest.fixture
def test_admin():
    """Admin user with 'superadmin' role."""
    return _make_test_user(
        user_id=TEST_ADMIN_ID, username="admin", email="admin@example.com", role="superadmin"
    )


# ────────────────────────────────────────────────────────────
# Auth header fixtures
# ────────────────────────────────────────────────────────────
def _create_auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    """Create a valid Bearer token header for the given user."""
    from app.core.security import create_access_token

    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(test_user) -> dict[str, str]:
    return _create_auth_headers(test_user.id)


@pytest.fixture
def admin_auth_headers(test_admin) -> dict[str, str]:
    return _create_auth_headers(test_admin.id)


# ────────────────────────────────────────────────────────────
# Dependency override helpers
# ────────────────────────────────────────────────────────────
@pytest.fixture
def override_get_db(mock_db):
    """Override get_db dependency to return mock_db."""
    from app.main import app
    from app.database import get_db

    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db_override
    yield mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def override_get_current_user(test_user):
    """Override get_current_user dependency to return test_user."""
    from app.main import app
    from app.api.deps import get_current_user

    async def _get_user_override():
        return test_user

    app.dependency_overrides[get_current_user] = _get_user_override
    yield test_user
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db, override_get_current_user) -> Generator[TestClient, None, None]:
    """TestClient with default auth and DB overrides."""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as tc:
        yield tc


# ────────────────────────────────────────────────────────────
# DB-override-only client (no auth — for anonymous/register)
# ────────────────────────────────────────────────────────────
@pytest.fixture
def anon_client(mock_db) -> Generator[TestClient, None, None]:
    """TestClient with DB override but no user override (anonymous)."""
    from fastapi.testclient import TestClient
    from app.database import get_db
    from app.main import app

    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


# ────────────────────────────────────────────────────────────
# Admin client
# ────────────────────────────────────────────────────────────
@pytest.fixture
def admin_client(mock_db, test_admin) -> Generator[TestClient, None, None]:
    """TestClient with admin user and DB override."""
    from fastapi.testclient import TestClient
    from app.api.deps import get_current_user
    from app.database import get_db
    from app.main import app

    async def _get_db_override():
        yield mock_db

    async def _get_admin_override():
        return test_admin

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_admin_override
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def create_auth_headers_for() -> Callable[[uuid.UUID], dict[str, str]]:
    """Factory for generating Bearer auth headers for arbitrary users."""
    return _create_auth_headers
