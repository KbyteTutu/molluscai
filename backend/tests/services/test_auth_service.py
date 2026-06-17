from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from jose import JWTError

from app.schemas.user import AuthResponse, PasswordChange, UserCreate
from app.services.auth_service import (
    authenticate_user,
    change_password,
    refresh_access_token,
    register_user,
)
from tests.conftest import MockResult, make_test_user


def _hydrate_user(user):
    user.balance = Decimal("0.00")
    user.daily_query_limit = None
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.mark.anyio
async def test_register_user_success(mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)
    payload = UserCreate(
        username="newuser",
        email="newuser@example.com",
        password="newpassword123",
    )

    async def refresh_user(user):
        user.id = uuid4()
        user.balance = Decimal("0.00")
        user.daily_query_limit = None
        user.created_at = datetime.now(timezone.utc)
        user.is_active = True

    mock_db.refresh.side_effect = refresh_user

    with patch("app.services.auth_service.hash_password", return_value="hashed-password"):
        response = await register_user(mock_db, payload)

    assert isinstance(response, AuthResponse)
    assert response.user.username == payload.username
    assert response.user.email == payload.email
    assert response.access_token
    assert response.refresh_token
    mock_db.add.assert_called_once()
    added_user = mock_db.add.call_args.args[0]
    assert added_user.username == payload.username
    assert added_user.email == payload.email
    assert added_user.role == "user"
    assert added_user.password_hash == "hashed-password"
    executed_stmt = mock_db.execute.await_args.args[0]
    compiled_stmt = str(executed_stmt.compile())
    assert "users.username" in compiled_stmt
    assert "users.email" in compiled_stmt
    mock_db.flush.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(added_user)


@pytest.mark.anyio
async def test_register_user_duplicate(mock_db):
    duplicate_user = _hydrate_user(make_test_user())
    mock_db.execute.return_value = MockResult(scalar_val=duplicate_user)
    payload = UserCreate(
        username=duplicate_user.username,
        email=duplicate_user.email,
        password="newpassword123",
    )

    with pytest.raises(ValueError, match="already exists"):
        await register_user(mock_db, payload)

    mock_db.add.assert_not_called()
    mock_db.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_authenticate_user_by_username(mock_db, test_user):
    _hydrate_user(test_user)
    mock_db.execute.return_value = MockResult(scalar_val=test_user)

    with patch("app.services.auth_service.verify_password", return_value=True) as verify_password:
        response = await authenticate_user(mock_db, test_user.username, "testpassword")

    assert isinstance(response, AuthResponse)
    assert response.user.username == test_user.username
    assert response.user.email == test_user.email
    verify_password.assert_called_once_with("testpassword", test_user.password_hash)


@pytest.mark.anyio
async def test_authenticate_user_by_email(mock_db, test_user):
    _hydrate_user(test_user)
    mock_db.execute.return_value = MockResult(scalar_val=test_user)

    with patch("app.services.auth_service.verify_password", return_value=True) as verify_password:
        response = await authenticate_user(mock_db, test_user.email, "testpassword")

    assert isinstance(response, AuthResponse)
    assert response.user.email == test_user.email
    verify_password.assert_called_once_with("testpassword", test_user.password_hash)


@pytest.mark.anyio
async def test_authenticate_user_wrong_password(mock_db, test_user):
    _hydrate_user(test_user)
    mock_db.execute.return_value = MockResult(scalar_val=test_user)

    with patch("app.services.auth_service.verify_password", return_value=False):
        response = await authenticate_user(mock_db, test_user.username, "wrong-password")

    assert response is None


@pytest.mark.anyio
async def test_authenticate_user_not_found(mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)

    response = await authenticate_user(mock_db, "missing-user", "password123")

    assert response is None


@pytest.mark.anyio
async def test_authenticate_user_inactive(mock_db, test_user):
    _hydrate_user(test_user)
    test_user.is_active = False
    mock_db.execute.return_value = MockResult(scalar_val=test_user)

    with patch("app.services.auth_service.verify_password", return_value=True):
        response = await authenticate_user(mock_db, test_user.username, "testpassword")

    assert response is None


@pytest.mark.anyio
async def test_refresh_access_token_valid(mock_db, test_user):
    _hydrate_user(test_user)
    mock_db.execute.return_value = MockResult(scalar_val=test_user)

    with patch(
        "app.services.auth_service.verify_token",
        return_value={"sub": str(test_user.id)},
    ) as verify_token:
        response = await refresh_access_token(mock_db, "refresh-token")

    assert response is not None
    assert response.access_token
    assert response.refresh_token
    assert response.token_type == "bearer"
    verify_token.assert_called_once_with("refresh-token", token_type="refresh")


@pytest.mark.anyio
async def test_refresh_access_token_expired(mock_db):
    with patch("app.services.auth_service.verify_token", side_effect=JWTError("expired")):
        response = await refresh_access_token(mock_db, "expired-token")

    assert response is None
    mock_db.execute.assert_not_awaited()


@pytest.mark.anyio
async def test_change_password_correct(mock_db):
    test_user = make_test_user()
    original_hash = test_user.password_hash
    payload = PasswordChange(old_password="testpassword", new_password="newpassword123")

    with patch("app.services.auth_service.verify_password", return_value=True), patch(
        "app.services.auth_service.hash_password",
        return_value="updated-password-hash",
    ):
        await change_password(mock_db, test_user, payload)

    assert test_user.password_hash != original_hash
    assert test_user.password_hash == "updated-password-hash"
    mock_db.flush.assert_awaited_once()


@pytest.mark.anyio
async def test_change_password_wrong_old(mock_db, test_user):
    payload = PasswordChange(old_password="wrongpassword", new_password="newpassword123")

    with patch("app.services.auth_service.verify_password", return_value=False):
        with pytest.raises(ValueError, match="incorrect"):
            await change_password(mock_db, test_user, payload)

    mock_db.flush.assert_not_awaited()
