from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import auction as auction_api
from app.api.v1 import taxa as taxa_api
from app.core.anonymous_rate_limit import AnonymousRateLimitResult
from app.database import get_db
from app.main import app
from app.schemas.taxon import TaxonSearchResponse
from tests.conftest import MockResult


class _EmptyMappingResult:
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
def _public_access_defaults(monkeypatch, mock_db):
    mock_db.execute.return_value = MockResult(rows=[], scalar_val=0)
    monkeypatch.setattr("app.main.bootstrap_app_settings", AsyncMock())
    monkeypatch.setattr(
        auction_api,
        "check_anonymous_search_rate_limit",
        AsyncMock(return_value=AnonymousRateLimitResult("203.0.113.10", True, 1, 20, 60)),
    )
    monkeypatch.setattr(
        taxa_api,
        "check_anonymous_search_rate_limit",
        AsyncMock(return_value=AnonymousRateLimitResult("203.0.113.10", True, 1, 20, 60)),
    )
    monkeypatch.setattr(auction_api, "search_auctions", AsyncMock(return_value=([], 0)))
    monkeypatch.setattr(auction_api, "log_query", AsyncMock())
    monkeypatch.setattr(auction_api, "get_auction_by_item_no", AsyncMock(return_value=None))
    monkeypatch.setattr(taxa_api, "lexical_search", AsyncMock(side_effect=_empty_taxa_search))
    monkeypatch.setattr(taxa_api, "hybrid_search", AsyncMock(side_effect=_empty_taxa_search))
    monkeypatch.setattr(taxa_api, "check_quota", AsyncMock())
    monkeypatch.setattr(taxa_api, "log_query", AsyncMock())
    monkeypatch.setattr(taxa_api, "_load_rank_names_zh", AsyncMock(return_value={}))


@pytest.fixture
def anon_client(mock_db):
    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_anonymous_can_use_auction_lexical_search(anon_client):
    response = anon_client.post(
        "/api/v1/auction/search",
        json={"name": "Conus", "mode": "lexical", "limit": 12},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    auction_api.log_query.assert_awaited_once()
    assert auction_api.log_query.await_args.kwargs["user"] is None
    assert auction_api.log_query.await_args.kwargs["ip_address"] == "203.0.113.10"


def test_anonymous_cannot_use_auction_smart_search(anon_client):
    response = anon_client.post(
        "/api/v1/auction/search",
        json={"name": "Conus", "mode": "hybrid", "limit": 12},
    )

    assert response.status_code == 401
    auction_api.log_query.assert_awaited_once()
    assert auction_api.log_query.await_args.kwargs["user"] is None
    assert auction_api.log_query.await_args.kwargs["status_code"] == 401


def test_anonymous_auction_search_is_ip_rate_limited(anon_client, monkeypatch):
    monkeypatch.setattr(
        auction_api,
        "check_anonymous_search_rate_limit",
        AsyncMock(return_value=AnonymousRateLimitResult("203.0.113.10", False, 21, 20, 42)),
    )

    response = anon_client.post(
        "/api/v1/auction/search",
        json={"name": "Conus", "mode": "lexical", "limit": 12},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"
    assert "登录" in response.json()["detail"]["message"]
    auction_api.log_query.assert_awaited_once()
    assert auction_api.log_query.await_args.kwargs["status_code"] == 429


def test_anonymous_can_open_auction_detail(anon_client):
    response = anon_client.get("/api/v1/auction/123")

    assert response.status_code == 404
    auction_api.get_auction_by_item_no.assert_awaited_once()


def test_anonymous_can_use_taxa_lexical_search(anon_client):
    response = anon_client.get(
        "/api/v1/taxa/search",
        params={"q": "Conus", "mode": "lexical", "limit": 20},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    taxa_api.log_query.assert_awaited_once()
    assert taxa_api.log_query.await_args.kwargs["user"] is None
    assert taxa_api.log_query.await_args.kwargs["ip_address"] == "203.0.113.10"


def test_anonymous_cannot_use_taxa_smart_search(anon_client):
    response = anon_client.get(
        "/api/v1/taxa/search",
        params={"q": "Conus", "mode": "hybrid", "limit": 20},
    )

    assert response.status_code == 401
    taxa_api.log_query.assert_awaited_once()
    assert taxa_api.log_query.await_args.kwargs["user"] is None
    assert taxa_api.log_query.await_args.kwargs["status_code"] == 401


def test_anonymous_taxa_search_is_ip_rate_limited(anon_client, monkeypatch):
    monkeypatch.setattr(
        taxa_api,
        "check_anonymous_search_rate_limit",
        AsyncMock(return_value=AnonymousRateLimitResult("203.0.113.10", False, 21, 20, 42)),
    )

    response = anon_client.get(
        "/api/v1/taxa/search",
        params={"q": "Conus", "mode": "lexical", "limit": 20},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"
    assert "登录" in response.json()["detail"]["message"]
    taxa_api.log_query.assert_awaited_once()
    assert taxa_api.log_query.await_args.kwargs["status_code"] == 429


def test_anonymous_can_open_taxon_detail(anon_client, mock_db):
    mock_db.execute.return_value = _EmptyMappingResult()

    response = anon_client.get("/api/v1/taxa/123")

    assert response.status_code == 404
