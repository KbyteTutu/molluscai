from __future__ import annotations

from decimal import Decimal

from app.services.taxa_search import _attach_match, _cost
from tests.conftest import MockRow


def test_cost_no_price() -> None:
    assert _cost(100, None, "per_1k_tokens") == Decimal("0")


def test_cost_per_1k() -> None:
    assert _cost(500, Decimal("0.01"), "per_1k_tokens") == Decimal("0.005")


def test_cost_per_1m() -> None:
    assert _cost(500000, Decimal("1.00"), "per_1m_tokens") == Decimal("0.5")


def test_cost_zero_tokens() -> None:
    assert _cost(0, Decimal("0.01"), "per_1k_tokens") == Decimal("0")


def test_attach_match_found() -> None:
    item = {"aphia_id": 1, "name": "test"}
    match_map = {1: {"kind": "name", "term": "Testus"}}

    result = _attach_match(item, match_map)

    assert result is not item
    assert result["match_info"].kind == "name"
    assert result["match_info"].term == "Testus"


def test_attach_match_not_found() -> None:
    item = {"aphia_id": 1, "name": "test"}

    result = _attach_match(item, {})

    assert result is item


def test_attach_match_aphia_id_string() -> None:
    item = MockRow(aphia_id="1", name="test")._mapping
    match_map = {1: {"kind": "name", "term": "Testus"}}

    result = _attach_match(item, match_map)

    assert result["match_info"].kind == "name"
    assert result["match_info"].term == "Testus"
