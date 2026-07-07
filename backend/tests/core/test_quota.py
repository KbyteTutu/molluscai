from __future__ import annotations

from datetime import datetime, timezone

from app.core.quota import (
    ALL_QUERY_TYPES,
    QUERY_TYPE_AI,
    QUERY_TYPE_AUCTION,
    QUERY_TYPE_TAXA,
    QUOTA_UNLIMITED,
    QuotaSnapshot,
    QuotaWindow,
    is_over_quota,
    log_query,
)
from tests.conftest import make_test_user


class TestIsOverQuota:
    def test_used_less_than_limit_returns_false(self) -> None:
        assert is_over_quota(used=4, limit=5) is False

    def test_used_equal_limit_returns_true(self) -> None:
        assert is_over_quota(used=5, limit=5) is True

    def test_used_greater_than_limit_returns_true(self) -> None:
        assert is_over_quota(used=6, limit=5) is True

    def test_unlimited_limit_always_returns_false(self) -> None:
        assert is_over_quota(used=0, limit=QUOTA_UNLIMITED) is False
        assert is_over_quota(used=100, limit=QUOTA_UNLIMITED) is False


class TestQuotaWindow:
    def test_creation_with_values(self) -> None:
        reset_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        window = QuotaWindow(used=3, limit=10, reset_at=reset_at)

        assert window.used == 3
        assert window.limit == 10
        assert window.reset_at == reset_at

    def test_remaining_when_under_limit(self) -> None:
        window = QuotaWindow(
            used=3,
            limit=10,
            reset_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        assert window.remaining == 7

    def test_remaining_when_over_limit(self) -> None:
        window = QuotaWindow(
            used=12,
            limit=10,
            reset_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        assert window.remaining == 0

    def test_remaining_when_unlimited_returns_negative_one(self) -> None:
        window = QuotaWindow(
            used=999,
            limit=QUOTA_UNLIMITED,
            reset_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        assert window.remaining == -1


class TestQuotaSnapshot:
    def test_creation_and_attribute_access(self) -> None:
        hourly = QuotaWindow(
            used=2,
            limit=5,
            reset_at=datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        )
        daily = QuotaWindow(
            used=7,
            limit=20,
            reset_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        snapshot = QuotaSnapshot(query_type=QUERY_TYPE_AI, hourly=hourly, daily=daily)

        assert snapshot.query_type == QUERY_TYPE_AI
        assert snapshot.hourly == hourly
        assert snapshot.daily == daily


def test_quota_constants() -> None:
    assert QUOTA_UNLIMITED == -1
    assert QUERY_TYPE_AI == "ai"
    assert QUERY_TYPE_AUCTION == "auction"
    assert QUERY_TYPE_TAXA == "taxa"
    assert ALL_QUERY_TYPES == (QUERY_TYPE_AI, QUERY_TYPE_AUCTION, QUERY_TYPE_TAXA)
from datetime import datetime, timezone

import pytest

from app.core.quota import (
    ALL_QUERY_TYPES,
    QUERY_TYPE_AI,
    QUERY_TYPE_AUCTION,
    QUERY_TYPE_TAXA,
    QUOTA_UNLIMITED,
    QuotaSnapshot,
    QuotaWindow,
    is_over_quota,
)


@pytest.mark.parametrize(
    ("used", "limit", "expected"),
    [
        (4, 5, False),
        (5, 5, True),
        (6, 5, True),
        (999, QUOTA_UNLIMITED, False),
    ],
)
def test_is_over_quota_handles_boundary_and_unlimited_values(
    used: int,
    limit: int,
    expected: bool,
):
    assert is_over_quota(used, limit) is expected


def test_quota_window_remaining_when_under_limit():
    window = QuotaWindow(
        used=3,
        limit=10,
        reset_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )

    assert window.remaining == 7


def test_quota_window_remaining_when_over_limit_is_clamped_to_zero():
    window = QuotaWindow(
        used=12,
        limit=10,
        reset_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )

    assert window.remaining == 0


def test_quota_window_remaining_when_unlimited_is_negative_one():
    window = QuotaWindow(
        used=500,
        limit=QUOTA_UNLIMITED,
        reset_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )

    assert window.remaining == -1


def test_quota_snapshot_creation_and_attributes():
    hourly = QuotaWindow(
        used=2,
        limit=5,
        reset_at=datetime(2030, 1, 1, 1, 0, tzinfo=timezone.utc),
    )
    daily = QuotaWindow(
        used=8,
        limit=20,
        reset_at=datetime(2030, 1, 2, 0, 0, tzinfo=timezone.utc),
    )

    snapshot = QuotaSnapshot(
        query_type=QUERY_TYPE_AI,
        hourly=hourly,
        daily=daily,
    )

    assert snapshot.query_type == QUERY_TYPE_AI
    assert snapshot.hourly is hourly
    assert snapshot.daily is daily
    assert snapshot.hourly.used == 2
    assert snapshot.daily.limit == 20


def test_quota_constants_have_expected_values():
    assert QUOTA_UNLIMITED == -1
    assert QUERY_TYPE_AI == "ai"
    assert QUERY_TYPE_AUCTION == "auction"
    assert QUERY_TYPE_TAXA == "taxa"
    assert ALL_QUERY_TYPES == (QUERY_TYPE_AI, QUERY_TYPE_AUCTION, QUERY_TYPE_TAXA)


@pytest.mark.anyio
async def test_log_query_flushes_without_committing(mock_db):
    await log_query(
        mock_db,
        user=make_test_user(),
        query_type=QUERY_TYPE_AUCTION,
        query_text="Conus",
        result_count=3,
        status_code=200,
    )

    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()
    mock_db.commit.assert_not_awaited()
