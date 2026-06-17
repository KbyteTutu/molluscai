from __future__ import annotations

from app.services.taxa_search import _rrf_fuse


def _rrf_score(rank: int, k: int) -> float:
    return 1.0 / (k + rank + 1)


def test_rrf_fuse_empty_and_single_source_inputs() -> None:
    assert _rrf_fuse([], []) == []
    assert _rrf_fuse([1, 2, 3], []) == [1, 2, 3]
    assert _rrf_fuse([], [4, 5, 6]) == [4, 5, 6]


def test_rrf_fuse_single_item_in_both_lists_ranks_first() -> None:
    assert _rrf_fuse([99], [99]) == [99]


def test_rrf_fuse_item_present_in_both_lists_scores_higher() -> None:
    result = _rrf_fuse([10, 20, 30], [30, 40, 50])

    assert result[0] == 30
    assert result.index(30) < result.index(10)
    assert result.index(30) < result.index(40)


def test_rrf_fuse_higher_ranked_items_get_higher_scores() -> None:
    result = _rrf_fuse([101, 102, 103, 104], [])

    assert result == [101, 102, 103, 104]


def test_rrf_fuse_custom_k_changes_scoring_weights() -> None:
    lexical = [1, 2, 3, 4, 5, 6]
    vector = [7, 8, 9, 10, 11, 6]

    low_k_gap = _rrf_score(0, 1) - _rrf_score(5, 1)
    high_k_gap = _rrf_score(0, 1_000) - _rrf_score(5, 1_000)

    assert low_k_gap > high_k_gap
    assert _rrf_fuse(lexical, vector, k=1) != _rrf_fuse(lexical, vector, k=1_000)


def test_rrf_fuse_returns_only_ids_from_inputs() -> None:
    lexical = [10, 20, 30]
    vector = [30, 40, 50]

    result = _rrf_fuse(lexical, vector)

    assert set(result).issubset(set(lexical) | set(vector))
    assert set(result) == {10, 20, 30, 40, 50}


def test_rrf_fuse_deduplicates_ids_repeated_within_same_list() -> None:
    result = _rrf_fuse([1, 1, 2, 2], [2, 2, 3, 3])

    assert result == [2, 1, 3]
    assert len(result) == 3


def test_rrf_fuse_handles_large_lists_negative_ids_and_large_k() -> None:
    lexical = list(range(-50, 950))
    vector = list(range(900, 1_900))

    result = _rrf_fuse(lexical, vector, k=100_000)

    assert result[0] == 900
    assert -50 in result
    assert 1_899 in result
    assert len(result) == len(set(lexical) | set(vector))
