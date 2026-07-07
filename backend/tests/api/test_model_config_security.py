from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.database import get_db
from app.main import app
from tests.conftest import MockResult, MockRow, make_test_user


def _model_payload(api_key: str = "sk-plain-secret") -> dict:
    return {
        "model_name": "Test Embedding",
        "provider": "openai_compat",
        "api_key": api_key,
        "base_url": "https://example.test/v1",
        "model_id": "embedding-model",
        "purpose": "embedding",
        "price_input": "0.01",
        "price_output": None,
        "price_unit": "per_1k_tokens",
        "is_active": True,
    }


def _created_row(api_key: str) -> MockRow:
    return MockRow(
        id=1,
        model_name="Test Embedding",
        provider="openai_compat",
        api_key=api_key,
        base_url="https://example.test/v1",
        model_id="embedding-model",
        purpose="embedding",
        price_input=Decimal("0.01"),
        price_output=None,
        price_unit="per_1k_tokens",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def test_create_model_encrypts_api_key_before_persisting(mock_db):
    async def _get_db_override():
        yield mock_db

    async def _get_admin_override():
        return make_test_user(role="superadmin")

    async def execute_side_effect(*args, **kwargs):
        params = args[1] if len(args) > 1 else kwargs
        if isinstance(params, dict) and "api_key" in params:
            assert params["api_key"].startswith("fernet:")
            assert params["api_key"] != "sk-plain-secret"
            return MockResult(rows=[_created_row(params["api_key"])])
        return MockResult(rows=[])

    mock_db.execute.side_effect = execute_side_effect
    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_admin_override

    with patch("app.main.bootstrap_app_settings", new=AsyncMock(return_value=None)):
        with TestClient(app) as client:
            response = client.post("/api/v1/admin/models", json=_model_payload())

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["api_key_tail"] == "...cret"


def test_doc_admin_cannot_manage_models(mock_db):
    async def _get_db_override():
        yield mock_db

    async def _get_doc_admin_override():
        return make_test_user(role="doc_admin")

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_doc_admin_override

    with patch("app.main.bootstrap_app_settings", new=AsyncMock(return_value=None)):
        with TestClient(app) as client:
            response = client.get("/api/v1/admin/models")

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
