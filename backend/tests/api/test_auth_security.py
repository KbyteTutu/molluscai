from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from jose import jwt

from app.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password
from tests.conftest import MockResult


@pytest.fixture(autouse=True)
def disable_app_startup(monkeypatch):
    async def _noop() -> None:
        return None

    monkeypatch.setattr("app.main.bootstrap_app_settings", _noop)


def build_user(
    *,
    user_id: uuid.UUID | None = None,
    username: str = "testuser",
    email: str = "test@example.com",
    role: str = "user",
    password: str = "Password123!",
    is_active: bool = True,
):
    return SimpleNamespace(
        id=user_id or uuid.uuid4(),
        username=username,
        email=email,
        role=role,
        balance=Decimal("0.00"),
        daily_query_limit=None,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        password_hash=hash_password(password),
    )


def auth_header_for_token(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def tamper_token_subject(token: str, new_subject: str) -> str:
    header, payload, signature = token.split(".")
    padding = "=" * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload + padding).decode("utf-8"))
    claims["sub"] = new_subject
    payload_bytes = json.dumps(claims, separators=(",", ":")).encode("utf-8")
    tampered_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    return f"{header}.{tampered_payload}.{signature}"


def prime_register_refresh(mock_db, *, user_id: uuid.UUID | None = None) -> None:
    async def _refresh(user) -> None:
        user.id = user_id or uuid.uuid4()
        user.balance = Decimal("0.00")
        user.daily_query_limit = None
        user.is_active = True
        user.created_at = datetime.now(timezone.utc)

    mock_db.refresh.side_effect = _refresh


@pytest.mark.parametrize(
    ("username", "email", "password"),
    [
        ("a" * 10000, "valid@example.com", "Password123!"),
        ("validuser", f"{'a' * 10000}@example.com", "Password123!"),
        ("validuser", "valid@example.com", "p" * 10000),
    ],
)
def test_register_oversized_fields(anon_client, username, email, password):
    response = anon_client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "username",
    ["admin' OR '1'='1", "<script>alert(1)</script>"],
)
def test_register_literal_attack_usernames(anon_client, mock_db, username):
    mock_db.execute.return_value = MockResult(scalar_val=None)
    prime_register_refresh(mock_db)

    response = anon_client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": "literal@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code in {201, 422}
    if response.status_code == 201:
        assert response.json()["user"]["username"] == username


def test_register_with_sql_injection_username(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)
    prime_register_refresh(mock_db)

    response = anon_client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin' OR '1'='1",
            "email": "sql@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code in {201, 422}
    if response.status_code == 201:
        assert response.json()["user"]["username"] == "admin' OR '1'='1"


def test_register_with_xss_username(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)
    prime_register_refresh(mock_db)

    response = anon_client.post(
        "/api/v1/auth/register",
        json={
            "username": "<script>alert(1)</script>",
            "email": "xss@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code in {201, 422}
    if response.status_code == 201:
        assert response.json()["user"]["username"] == "<script>alert(1)</script>"


def test_register_with_null_bytes(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)
    prime_register_refresh(mock_db)

    response = anon_client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin\u0000bypass",
            "email": "nullbyte@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code in {201, 422}


def test_login_sql_injection(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)

    response = anon_client.post(
        "/api/v1/auth/login",
        json={"username": "' OR 1=1 --", "password": "irrelevant-password"},
    )

    assert response.status_code == 401


def test_login_unicode_normalization(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)

    response = anon_client.post(
        "/api/v1/auth/login",
        json={"username": "аdmin", "password": "Password123!"},
    )

    assert response.status_code == 401


def test_login_brute_force_like(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)

    responses = [
        anon_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": f"wrong-{attempt}"},
        )
        for attempt in range(5)
    ]

    assert {response.status_code for response in responses} == {401}
    assert {response.json()["detail"] for response in responses} == {"Invalid username or password"}


def test_login_with_null_bytes(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)

    response = anon_client.post(
        "/api/v1/auth/login",
        json={"username": "admin\u0000", "password": "Password123!"},
    )

    assert response.status_code in {401, 422}


def test_access_protected_route_without_token(anon_client):
    response = anon_client.get("/api/v1/auth/me")

    assert response.status_code in {401, 403}


def test_access_with_empty_token(anon_client):
    response = anon_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer "},
    )

    assert response.status_code in {401, 403}


def test_access_with_malformed_token(anon_client):
    response = anon_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.jwt"},
    )

    assert response.status_code == 401


def test_access_with_expired_token(anon_client):
    token = create_access_token(
        subject=str(uuid.uuid4()),
        expires_delta=timedelta(minutes=-5),
    )

    response = anon_client.get(
        "/api/v1/auth/me",
        headers=auth_header_for_token(token),
    )

    assert response.status_code == 401


def test_access_with_tampered_token(anon_client):
    token = create_access_token(subject=str(uuid.uuid4()))
    tampered = tamper_token_subject(token, str(uuid.uuid4()))

    response = anon_client.get(
        "/api/v1/auth/me",
        headers=auth_header_for_token(tampered),
    )

    assert response.status_code == 401


def test_access_with_wrong_token_type(anon_client):
    token = create_refresh_token(subject=str(uuid.uuid4()))

    response = anon_client.get(
        "/api/v1/auth/me",
        headers=auth_header_for_token(token),
    )

    assert response.status_code == 401


def test_access_with_revoked_style_token(anon_client, mock_db):
    user = build_user()
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"iat": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())},
    )
    mock_db.execute.return_value = MockResult(scalar_val=user)

    response = anon_client.get(
        "/api/v1/auth/me",
        headers=auth_header_for_token(token),
    )

    assert response.status_code in {200, 401}


def test_refresh_with_access_token(anon_client):
    response = anon_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": create_access_token(subject=str(uuid.uuid4()))},
    )

    assert response.status_code == 401


def test_token_with_empty_subject(anon_client, mock_db):
    token = create_access_token(subject="")
    mock_db.execute.return_value = MockResult(scalar_val=None)

    response = anon_client.get(
        "/api/v1/auth/me",
        headers=auth_header_for_token(token),
    )

    assert response.status_code == 401


def test_token_algorithm_confusion(anon_client):
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "type": "access",
        },
        settings.JWT_SECRET_KEY,
        algorithm="HS512",
    )

    response = anon_client.get(
        "/api/v1/auth/me",
        headers=auth_header_for_token(token),
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/admin/scraper/stats", None),
        ("post", "/api/v1/admin/scraper/run", {"batch_size": 1}),
        ("get", "/api/v1/admin/models", None),
        ("get", "/api/v1/admin/tasks", None),
        ("post", "/api/v1/admin/embed/run", {"rebuild": False}),
        ("get", "/api/v1/admin/quotas", None),
        ("get", "/api/v1/admin/users", None),
        ("patch", "/api/v1/admin/corrections/1", {"status": "approved"}),
    ],
)
def test_regular_user_cannot_access_admin_endpoints(
    anon_client,
    auth_headers,
    mock_db,
    test_user,
    method,
    path,
    payload,
):
    regular_user = build_user(user_id=test_user.id, username=test_user.username, email=test_user.email)
    mock_db.execute.return_value = MockResult(scalar_val=regular_user)

    request_kwargs = {"headers": auth_headers}
    if payload is not None:
        request_kwargs["json"] = payload
    response = getattr(anon_client, method)(path, **request_kwargs)

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_register_success(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)
    prime_register_refresh(mock_db)

    response = anon_client.post(
        "/api/v1/auth/register",
        json={
            "username": "freshuser",
            "email": "fresh@example.com",
            "password": "Password123!",
        },
    )

    data = response.json()
    assert response.status_code == 201
    assert data["user"]["username"] == "freshuser"
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]


def test_register_duplicate(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=build_user())

    response = anon_client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 409


def test_login_success(anon_client, mock_db):
    user = build_user(password="Password123!")
    mock_db.execute.return_value = MockResult(scalar_val=user)

    response = anon_client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "Password123!"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["user"]["username"] == user.username
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]


def test_login_invalid(anon_client, mock_db):
    user = build_user(password="CorrectPassword123!")
    mock_db.execute.return_value = MockResult(scalar_val=user)

    response = anon_client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "WrongPassword123!"},
    )

    assert response.status_code == 401


def test_login_nonexistent(anon_client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)

    response = anon_client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "Password123!"},
    )

    assert response.status_code == 401


def test_get_me_authenticated(anon_client, auth_headers, mock_db, test_user):
    user = build_user(user_id=test_user.id, username=test_user.username, email=test_user.email)
    mock_db.execute.return_value = MockResult(scalar_val=user)

    response = anon_client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["username"] == test_user.username


def test_change_password_success(anon_client, auth_headers, mock_db, test_user):
    user = build_user(
        user_id=test_user.id,
        username=test_user.username,
        email=test_user.email,
        password="OldPassword123!",
    )
    mock_db.execute.return_value = MockResult(scalar_val=user)

    response = anon_client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"old_password": "OldPassword123!", "new_password": "NewPassword123!"},
    )

    assert response.status_code == 200
    assert response.json()["detail"] == "Password changed successfully"


def test_change_password_wrong_old(anon_client, auth_headers, mock_db, test_user):
    user = build_user(
        user_id=test_user.id,
        username=test_user.username,
        email=test_user.email,
        password="OldPassword123!",
    )
    mock_db.execute.return_value = MockResult(scalar_val=user)

    response = anon_client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"old_password": "NotTheOldPassword123!", "new_password": "NewPassword123!"},
    )

    assert response.status_code == 400


def test_health_endpoint_no_auth(anon_client):
    response = anon_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
