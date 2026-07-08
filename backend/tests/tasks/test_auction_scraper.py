from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.tasks import auction_scraper


@pytest.mark.anyio
async def test_probe_reached_end_when_all_probe_offsets_missing(monkeypatch) -> None:
    calls: list[int] = []

    async def fake_fetch(_session, item_id, _sem):
        calls.append(item_id)
        return None

    monkeypatch.setattr(auction_scraper, "_fetch_one", fake_fetch)

    reached_end, checked = await auction_scraper._probe_reached_end(SimpleNamespace(), 100, SimpleNamespace())

    assert reached_end is True
    assert checked == 5
    assert calls == [101, 103, 105, 110, 150]


@pytest.mark.anyio
async def test_probe_stops_when_a_later_probe_exists(monkeypatch) -> None:
    calls: list[int] = []

    async def fake_fetch(_session, item_id, _sem):
        calls.append(item_id)
        if item_id == 105:
            return auction_scraper.BidItem(item_no=item_id, name="Found")
        return None

    monkeypatch.setattr(auction_scraper, "_fetch_one", fake_fetch)

    reached_end, checked = await auction_scraper._probe_reached_end(SimpleNamespace(), 100, SimpleNamespace())

    assert reached_end is False
    assert checked == 3
    assert calls == [101, 103, 105]
