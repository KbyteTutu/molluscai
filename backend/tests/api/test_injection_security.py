from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1 import auction as auction_api
from app.api.v1 import taxa as taxa_api
from app.database import get_db
from app.main import app
from app.schemas.taxon import TaxonSearchResponse
from tests.conftest import MockResult


class _FakeRedis:
    def get(self, *_args, **_kwargs):
        return None

    def setex(self, *_args, **_kwargs):
        return None


class _EmptyTaxonDetailResult:
    def mappings(self):
        return self

    def first(self):
        return None


async def _empty_taxa_search(*_args, **kwargs):
    return TaxonSearchResponse(
        items=[],
        total=0,
        offset=kwargs.get("offset", 0),
        limit=kwargs.get("limit", 20),
        rank_names_zh={},
    )


@pytest.fixture(autouse=True)
def _security_test_defaults(monkeypatch, mock_db):
    mock_db.execute.return_value = MockResult(rows=[], scalar_val=0)

    monkeypatch.setattr(taxa_api, "check_quota", AsyncMock())
    monkeypatch.setattr(taxa_api, "log_query", AsyncMock())
    monkeypatch.setattr(taxa_api, "_load_rank_names_zh", AsyncMock(return_value={}))
    monkeypatch.setattr(taxa_api, "lexical_search", AsyncMock(side_effect=_empty_taxa_search))
    monkeypatch.setattr(taxa_api, "hybrid_search", AsyncMock(side_effect=_empty_taxa_search))

    monkeypatch.setattr(auction_api, "check_quota", AsyncMock())
    monkeypatch.setattr(auction_api, "log_query", AsyncMock())
    monkeypatch.setattr(auction_api, "search_auctions", AsyncMock(return_value=([], 0)))
    monkeypatch.setattr(auction_api, "get_auction_by_item_no", AsyncMock(return_value=None))
    monkeypatch.setattr(auction_api, "_redis", lambda: _FakeRedis())
    monkeypatch.setattr("app.main.bootstrap_app_settings", AsyncMock())


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


def test_taxa_search_sql_injection_basic(client):
    response = client.get("/api/v1/taxa/search", params={"q": "'; DROP TABLE taxa; --"})
    assert response.status_code == 200


def test_taxa_search_sql_injection_union(client):
    response = client.get("/api/v1/taxa/search", params={"q": "' UNION SELECT * FROM users--"})
    assert response.status_code == 200
    assert "users" not in response.text.lower()


def test_taxa_search_sql_injection_comment(client):
    response = client.get("/api/v1/taxa/search", params={"q": "test'--"})
    assert response.status_code == 200


def test_taxa_search_sql_injection_semicolon(client):
    response = client.get("/api/v1/taxa/search", params={"q": "test; DELETE FROM taxa"})
    assert response.status_code == 200


def test_taxa_search_sql_injection_rank_param(client):
    response = client.get("/api/v1/taxa/search", params={"q": "", "rank": "'; DROP TABLE--"})
    assert response.status_code == 200


def test_taxa_search_sql_injection_family_param(client):
    response = client.get(
        "/api/v1/taxa/search",
        params={"q": "", "family": "Conidae'; SELECT * FROM users--"},
    )
    assert response.status_code == 200


def test_taxa_search_empty_query(client):
    response = client.get("/api/v1/taxa/search", params={"q": ""})
    assert response.status_code == 200


def test_taxa_search_oversized_query(client):
    response = client.get("/api/v1/taxa/search", params={"q": "a" * 10000})
    assert response.status_code == 200


def test_taxa_search_negative_offset(client):
    response = client.get("/api/v1/taxa/search", params={"q": "", "offset": -1})
    assert response.status_code == 422


def test_taxa_search_excessive_limit(client):
    response = client.get("/api/v1/taxa/search", params={"q": "", "limit": 99999})
    assert response.status_code == 422


def test_taxa_statuses_sql_injection(client):
    response = client.get("/api/v1/taxa/statuses")
    assert response.status_code == 200


def test_taxa_detail_non_numeric_aphia_id(client):
    response = client.get("/api/v1/taxa/abc")
    assert response.status_code == 422


def test_taxa_detail_negative_aphia_id(client, mock_db):
    mock_db.execute.return_value = _EmptyTaxonDetailResult()
    response = client.get("/api/v1/taxa/-1")
    assert response.status_code == 404


def test_taxa_detail_path_traversal(client):
    response = client.get("/api/v1/taxa/%2E%2E%2F%2E%2E%2F%2E%2E%2Fetc%2Fpasswd")
    assert response.status_code in {404, 422}


def test_worms_lookup_sql_injection(client, monkeypatch):
    class _FakeResp:
        status_code = 200

        def json(self):
            return [{"AphiaID": 1, "scientificname": "Safe shell", "authority": None}]

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *_args, **_kwargs):
            return _FakeResp()

    monkeypatch.setattr(taxa_api.httpx, "AsyncClient", _FakeClient)
    response = client.get("/api/v1/taxa/worms-lookup", params={"q": "' OR 1=1 --"})
    assert response.status_code == 200


def test_worms_lookup_xss_reflected(client, monkeypatch):
    class _FakeResp:
        status_code = 200

        def json(self):
            return [{"AphiaID": 1, "scientificname": "Safe shell", "authority": None}]

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *_args, **_kwargs):
            return _FakeResp()

    monkeypatch.setattr(taxa_api.httpx, "AsyncClient", _FakeClient)
    payload = "<script>alert(1)</script>"
    response = client.get("/api/v1/taxa/worms-lookup", params={"q": payload})
    assert response.status_code == 200
    assert payload not in response.text


def test_worms_lookup_empty_query(client):
    response = client.get("/api/v1/taxa/worms-lookup", params={"q": "a"})
    assert response.status_code == 422


def test_worms_lookup_very_long_query(client, monkeypatch):
    class _FakeResp:
        status_code = 200

        def json(self):
            return []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *_args, **_kwargs):
            return _FakeResp()

    monkeypatch.setattr(taxa_api.httpx, "AsyncClient", _FakeClient)
    response = client.get("/api/v1/taxa/worms-lookup", params={"q": "a" * 2000})
    assert response.status_code == 200


def test_auction_search_sql_injection_name(client):
    response = client.post("/api/v1/auction/search", json={"name": "'; DROP TABLE --"})
    assert response.status_code == 200


def test_auction_search_sql_injection_family(client):
    response = client.post("/api/v1/auction/search", json={"family": "'; DELETE FROM auctions --"})
    assert response.status_code == 200


def test_auction_search_sql_injection_locality(client):
    response = client.post("/api/v1/auction/search", json={"locality": "x'; SELECT * FROM auctions --"})
    assert response.status_code == 200


def test_auction_search_sql_injection_seller(client):
    response = client.post("/api/v1/auction/search", json={"seller": "'; DROP TABLE sellers --"})
    assert response.status_code == 200


def test_auction_search_negative_size_min(client):
    response = client.post("/api/v1/auction/search", json={"size_min": -100})
    assert response.status_code == 200


def test_auction_search_size_min_greater_than_max(client):
    response = client.post("/api/v1/auction/search", json={"size_min": 100, "size_max": 10})
    assert response.status_code == 200


def test_auction_get_detail_non_numeric(client):
    response = client.get("/api/v1/auction/abc")
    assert response.status_code == 422


def test_auction_get_detail_negative(client):
    response = client.get("/api/v1/auction/-999")
    assert response.status_code in {404, 422}


def test_auction_families_sql_injection(client):
    response = client.get("/api/v1/auction/families", params={"q": "'; DROP TABLE--"})
    assert response.status_code == 200


def test_auction_recent_no_auth(anon_client):
    response = anon_client.get("/api/v1/auction/recent")
    assert response.status_code == 200


def test_search_with_unicode_confusables(client):
    response = client.get("/api/v1/taxa/search", params={"q": "ｍｕｓｓｅｌ∕shell"})
    assert response.status_code == 200


def test_search_with_binary_data(client):
    response = client.get("/api/v1/taxa/search?q=%FF%FE")
    assert response.status_code < 500


def test_search_with_emoji_flood(client):
    response = client.get("/api/v1/taxa/search", params={"q": "🦪" * 100})
    assert response.status_code == 200
