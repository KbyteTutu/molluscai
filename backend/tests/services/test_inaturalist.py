from __future__ import annotations

import pytest

from app.services.inaturalist import (
    InatResult,
    _LOCALE_MAP,
    _RANK_MAP,
    _locale_to_lang,
    _map_rank,
    extract_vernaculars,
)


@pytest.mark.parametrize("db_rank, expected", [(rank, mapped) for rank, mapped in _RANK_MAP.items()])
def test_map_rank_covers_every_known_rank(db_rank: str, expected: str) -> None:
    assert _map_rank(db_rank) == expected


def test_map_rank_handles_common_values_and_invalid_inputs() -> None:
    assert _map_rank("Species") == "species"
    assert _map_rank("Genus") == "genus"
    assert _map_rank("Family") == "family"
    assert _map_rank(None) is None
    assert _map_rank("InvalidRank") is None


@pytest.mark.parametrize(
    ("locale", "expected"),
    [
        ("zh", "CHN"),
        ("zh-CN", "CHN"),
        ("en", "ENG"),
        ("ja", "JPN"),
        ("fr", "FRA"),
        ("de", "DEU"),
        ("xx", "XX"),
        ("", "OTH"),
    ],
)
def test_locale_to_lang_maps_known_and_fallback_values(locale: str, expected: str) -> None:
    assert _locale_to_lang(locale) == expected


def test_locale_to_lang_matches_declared_locale_map() -> None:
    for locale, language_code in _LOCALE_MAP.items():
        assert _locale_to_lang(locale) == language_code


def test_extract_vernaculars_extracts_valid_names_and_filters_invalid_entries() -> None:
    taxon = {
        "names": [
            {"name": "Moon Snail", "locale": "en", "is_valid": True},
            {"name": "  Moon Snail  ", "locale": "en", "is_valid": True},
            {"name": "月亮螺", "locale": "zh-CN", "is_valid": True},
            {"name": "Mondschnecke", "locale": "de", "is_valid": True},
            {"name": "Moon Snail", "locale": "en", "is_valid": False},
            {"name": "Never kept", "locale": "sci", "is_valid": True},
            {"name": "", "locale": "fr", "is_valid": True},
        ]
    }

    assert extract_vernaculars(taxon) == [
        {"vernacular": "Moon Snail", "language_code": "ENG"},
        {"vernacular": "月亮螺", "language_code": "CHN"},
        {"vernacular": "Mondschnecke", "language_code": "DEU"},
    ]


def test_extract_vernaculars_handles_empty_and_missing_names() -> None:
    assert extract_vernaculars({"names": []}) == []
    assert extract_vernaculars({}) == []


def test_inat_result_defaults() -> None:
    result = InatResult()

    assert result.found is False
    assert result.inat_id is None
    assert result.preferred_common_name is None
    assert result.observations_count is None
    assert result.wikipedia_url is None
    assert result.wikipedia_summary is None
    assert result.image_url is None
    assert result.conservation_status is None
    assert result.vernaculars == []


def test_inat_result_accepts_all_fields() -> None:
    vernaculars = [{"vernacular": "Moon Snail", "language_code": "ENG"}]

    result = InatResult(
        found=True,
        inat_id=42,
        preferred_common_name="Moon Snail",
        observations_count=1234,
        wikipedia_url="https://example.org/wiki/moon-snail",
        wikipedia_summary="A predatory sea snail.",
        image_url="https://example.org/moon-snail.jpg",
        conservation_status="Least Concern",
        vernaculars=vernaculars,
    )

    assert result.found is True
    assert result.inat_id == 42
    assert result.preferred_common_name == "Moon Snail"
    assert result.observations_count == 1234
    assert result.wikipedia_url == "https://example.org/wiki/moon-snail"
    assert result.wikipedia_summary == "A predatory sea snail."
    assert result.image_url == "https://example.org/moon-snail.jpg"
    assert result.conservation_status == "Least Concern"
    assert result.vernaculars == vernaculars
