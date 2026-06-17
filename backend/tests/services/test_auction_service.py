from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.schemas.auction import AuctionSearchRequest
from app.services.auction_service import (
    _build_condition_text,
    _build_conditions,
    _sort_columns,
    _sort_text,
    get_auction_by_item_no,
)
from tests.conftest import MockResult, MockRow


def _compile(expr) -> str:
    return str(expr.compile(compile_kwargs={"literal_binds": True}))


def test_build_conditions_empty() -> None:
    assert _build_conditions(AuctionSearchRequest()) == []


def test_build_conditions_name() -> None:
    conditions = _build_conditions(AuctionSearchRequest(name="Conus"))

    assert len(conditions) == 1
    assert "similarity(auctions.name, 'Conus') > 0.1" in _compile(conditions[0])


def test_build_conditions_family() -> None:
    conditions = _build_conditions(AuctionSearchRequest(family="Conidae"))

    assert len(conditions) == 1
    compiled = _compile(conditions[0])
    assert "auctions.family" in compiled
    assert "Conidae" in compiled


def test_build_conditions_size_min_max() -> None:
    conditions = _build_conditions(
        AuctionSearchRequest(size_min=Decimal("10"), size_max=Decimal("20"))
    )
    compiled = [_compile(condition) for condition in conditions]
    joined = " ".join(compiled)

    assert "regexp_replace" in joined
    assert "IS NOT NULL" in joined
    assert ">= 10" in joined
    assert "<= 20" in joined


def test_build_conditions_price_range() -> None:
    conditions = _build_conditions(
        AuctionSearchRequest(price_min=Decimal("100"), price_max=Decimal("250"))
    )
    compiled = [_compile(condition) for condition in conditions]

    assert "auctions.final_price >= 100" in compiled[0]
    assert "auctions.final_price <= 250" in compiled[1]


def test_build_conditions_is_sold() -> None:
    true_conditions = _build_conditions(AuctionSearchRequest(is_sold=True))
    false_conditions = _build_conditions(AuctionSearchRequest(is_sold=False))

    assert "auctions.is_sold = true" in _compile(true_conditions[0])
    assert "auctions.is_sold = false" in _compile(false_conditions[0])


def test_build_conditions_date_range() -> None:
    conditions = _build_conditions(
        AuctionSearchRequest(
            end_date_from=date(2024, 1, 1),
            end_date_to=date(2024, 1, 31),
        )
    )
    compiled = [_compile(condition) for condition in conditions]

    assert "auctions.end_date >= '2024-01-01'" in compiled[0]
    assert "auctions.end_date <= '2024-01-31'" in compiled[1]


def test_build_conditions_seller() -> None:
    conditions = _build_conditions(AuctionSearchRequest(seller="Sheller"))

    assert len(conditions) == 1
    compiled = _compile(conditions[0])
    assert "auctions.seller" in compiled
    assert "Sheller" in compiled


def test_build_conditions_combined() -> None:
    conditions = _build_conditions(
        AuctionSearchRequest(
            name="Conus",
            family="Conidae",
            price_min=Decimal("100"),
            is_sold=True,
            seller="Sheller",
        )
    )
    compiled = " ".join(_compile(condition) for condition in conditions)

    assert "similarity(auctions.name, 'Conus') > 0.1" in compiled
    assert "auctions.family" in compiled
    assert "Conidae" in compiled
    assert "auctions.final_price >= 100" in compiled
    assert "auctions.is_sold = true" in compiled
    assert "auctions.seller" in compiled
    assert "Sheller" in compiled


def test_build_condition_text_empty() -> None:
    assert _build_condition_text(AuctionSearchRequest()) == ("TRUE", {})


def test_build_condition_text_name() -> None:
    clause, params = _build_condition_text(AuctionSearchRequest(name="Conus"))

    assert clause == "similarity(a.name, :name) > 0.1"
    assert params == {"name": "Conus"}


def test_build_condition_text_family() -> None:
    clause, params = _build_condition_text(AuctionSearchRequest(family="Conidae"))

    assert clause == "a.family ILIKE :family"
    assert params == {"family": "%Conidae%"}


def test_sort_columns() -> None:
    price_desc = [_compile(column) for column in _sort_columns(AuctionSearchRequest(sort="price_desc"))]
    price_asc = [_compile(column) for column in _sort_columns(AuctionSearchRequest(sort="price_asc"))]
    item_no_desc = [_compile(column) for column in _sort_columns(AuctionSearchRequest(sort="item_no_desc"))]
    end_date_desc = [_compile(column) for column in _sort_columns(AuctionSearchRequest(sort="end_date_desc"))]
    relevance = [_compile(column) for column in _sort_columns(AuctionSearchRequest(name="Conus", sort="relevance"))]

    assert "auctions.final_price DESC NULLS LAST" in price_desc[0]
    assert "auctions.final_price ASC NULLS LAST" in price_asc[0]
    assert "auctions.item_no DESC" in item_no_desc[0]
    assert "auctions.end_date DESC NULLS LAST" in end_date_desc[0]
    assert "similarity(auctions.name, 'Conus') DESC" in relevance[0]


def test_sort_text() -> None:
    assert _sort_text(AuctionSearchRequest(name="Conus")) == (
        "similarity(a.name, :name) DESC, a.end_date DESC NULLS LAST"
    )
    assert _sort_text(AuctionSearchRequest()) == "a.end_date DESC NULLS LAST"


@pytest.mark.anyio
async def test_get_auction_by_item_no_found(mock_db) -> None:
    mock_db.execute.return_value = MockResult(
        scalar_val=MockRow(item_no=1, name="Test Auction")
    )

    result = await get_auction_by_item_no(mock_db, 1)

    assert result is not None
    assert result.item_no == 1
    assert result.name == "Test Auction"


@pytest.mark.anyio
async def test_get_auction_by_item_no_not_found(mock_db) -> None:
    mock_db.execute.return_value = MockResult(scalar_val=None)

    result = await get_auction_by_item_no(mock_db, 1)

    assert result is None
