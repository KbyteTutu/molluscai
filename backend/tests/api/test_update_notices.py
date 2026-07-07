from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.database import get_db
from app.main import app
from tests.conftest import MockResult, make_test_user


def test_public_update_notices_returns_defaults_when_unset(mock_db):
    async def _get_db_override():
        yield mock_db

    mock_db.execute.return_value = MockResult(scalar_val=None)
    app.dependency_overrides[get_db] = _get_db_override

    with patch("app.main.bootstrap_app_settings", new=AsyncMock(return_value=None)):
        with TestClient(app) as client:
            response = client.get("/api/v1/public/update-notices")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    assert body["items"][0]["title"]


def test_admin_can_update_notices(mock_db):
    async def _get_db_override():
        yield mock_db

    async def _get_admin_override():
        return make_test_user(role="superadmin")

    mock_db.execute.return_value = MockResult(rows=[])
    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_admin_override

    payload = {
        "items": [
            {"date": "2026-07-08", "title": "公告编辑", "text": "后台可修改更新公告。"}
        ]
    }
    with patch("app.main.bootstrap_app_settings", new=AsyncMock(return_value=None)):
        with TestClient(app) as client:
            response = client.patch("/api/v1/admin/settings/update-notices", json=payload)

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == payload
    mock_db.commit.assert_awaited_once()


def test_update_notices_rejects_blank_items(mock_db):
    async def _get_db_override():
        yield mock_db

    async def _get_admin_override():
        return make_test_user(role="superadmin")

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_admin_override

    with patch("app.main.bootstrap_app_settings", new=AsyncMock(return_value=None)):
        with TestClient(app) as client:
            response = client.patch(
                "/api/v1/admin/settings/update-notices",
                json={"items": [{"date": "", "title": "", "text": ""}]},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 422
