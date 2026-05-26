from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

log = logging.getLogger("inaturalist")

INAT_BASE = "https://api.inaturalist.org/v1"
HEADERS = {
    "User-Agent": "MolluscAI/1.0 (molluscai.com)",
}

# iNaturalist locale → our language_code mapping
_LOCALE_MAP: dict[str, str] = {
    "zh": "CHN",
    "zh-CN": "CHN",
    "zh-TW": "CHN",
    "en": "ENG",
    "ja": "JPN",
    "ko": "KOR",
    "fr": "FRA",
    "de": "DEU",
    "es": "ESP",
    "it": "ITA",
    "nl": "NLD",
    "pt": "POR",
    "ru": "RUS",
    "ar": "ARA",
    "he": "HEB",
    "th": "THA",
    "pl": "POL",
    "cs": "CES",
    "sk": "SLK",
    "tr": "TUR",
    "vi": "VIE",
    "id": "IND",
    "ms": "MSA",
    "tl": "TGL",
    "sw": "SWA",
    "el": "ELL",
    "fi": "FIN",
    "sv": "SWE",
    "no": "NOR",
    "da": "DAN",
    "hu": "HUN",
    "ro": "RON",
    "ca": "CAT",
    "eu": "EUS",
}

# our rank → iNaturalist rank
_RANK_MAP: dict[str, str] = {
    "Species": "species",
    "Subspecies": "subspecies",
    "Genus": "genus",
    "Subgenus": "subgenus",
    "Family": "family",
    "Subfamily": "subfamily",
    "Superfamily": "superfamily",
    "Order": "order",
    "Suborder": "suborder",
    "Infraorder": "infraorder",
    "Superorder": "superorder",
    "Class": "class",
    "Subclass": "subclass",
    "Infraclass": "infraclass",
    "Phylum": "phylum",
    "Subphylum": "subphylum",
    "Kingdom": "kingdom",
    "Tribe": "tribe",
    "Variety": "variety",
    "Forma": "form",
}

RANKS_WITH_VERNACULARS = frozenset(["species", "genus", "family"])


def _map_rank(db_rank: str | None) -> str | None:
    if not db_rank:
        return None
    return _RANK_MAP.get(db_rank)


def _locale_to_lang(locale: str) -> str:
    """Map iNaturalist locale to our 3-letter language_code."""
    return _LOCALE_MAP.get(locale, locale.split("-")[0].upper() if locale else "OTH")


@dataclass
class InatResult:
    found: bool = False
    inat_id: Optional[int] = None
    preferred_common_name: Optional[str] = None
    observations_count: Optional[int] = None
    wikipedia_url: Optional[str] = None
    wikipedia_summary: Optional[str] = None
    image_url: Optional[str] = None
    conservation_status: Optional[str] = None
    vernaculars: list[dict[str, str]] = field(default_factory=list)


async def search_exact_match(scientific_name: str, rank: str | None = None) -> Optional[dict]:
    """Search iNaturalist for an exact scientific name match at the given rank."""
    params: dict[str, str | int] = {
        "q": scientific_name,
        "per_page": 10,
    }
    if rank:
        params["rank"] = rank
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            resp = await client.get(f"{INAT_BASE}/taxa", params=params)
            if resp.status_code != 200:
                log.warning("iNat search HTTP %d for %s", resp.status_code, scientific_name)
                return None
            data = resp.json()
    except Exception as exc:
        log.warning("iNat search error for %s: %s", scientific_name, exc)
        return None

    results = data.get("results", [])
    target = scientific_name.lower().strip()
    for taxon in results:
        if taxon.get("name", "").lower().strip() == target:
            return taxon
    return None


async def get_taxon_detail(inat_id: int) -> Optional[dict]:
    """Fetch full taxon detail from iNaturalist with all vernacular names."""
    params = {"all_names": "true"}
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            resp = await client.get(f"{INAT_BASE}/taxa/{inat_id}", params=params)
            if resp.status_code != 200:
                log.warning("iNat detail HTTP %d for id %d", resp.status_code, inat_id)
                return None
            data = resp.json()
    except Exception as exc:
        log.warning("iNat detail error for id %d: %s", inat_id, exc)
        return None

    results = data.get("results", [])
    return results[0] if results else None


def extract_vernaculars(taxon: dict) -> list[dict[str, str]]:
    """Extract valid vernacular names from iNaturalist taxon detail."""
    out: list[dict[str, str]] = []
    seen = set()
    for n in taxon.get("names", []):
        if not n.get("is_valid"):
            continue
        name = n.get("name", "").strip()
        locale = n.get("locale", "")
        if not name or locale == "sci":
            continue
        lang_code = _locale_to_lang(locale)
        key = (name.lower(), lang_code)
        if key in seen:
            continue
        seen.add(key)
        out.append({"vernacular": name, "language_code": lang_code})
    return out


async def lookup(scientific_name: str, rank: str | None = None) -> InatResult:
    """Full iNaturalist lookup: search → detail → vernacular extraction."""
    inat_rank = _map_rank(rank)
    taxon = await search_exact_match(scientific_name, inat_rank)
    if not taxon:
        return InatResult()

    inat_id = taxon["id"]
    detail = await get_taxon_detail(inat_id)
    if not detail:
        return InatResult(
            found=True,
            inat_id=inat_id,
            preferred_common_name=taxon.get("preferred_common_name", "") or None,
            observations_count=taxon.get("observations_count"),
            wikipedia_url=taxon.get("wikipedia_url") or None,
        )

    photo = detail.get("default_photo")
    return InatResult(
        found=True,
        inat_id=inat_id,
        preferred_common_name=detail.get("preferred_common_name", "") or None,
        observations_count=detail.get("observations_count"),
        wikipedia_url=detail.get("wikipedia_url") or None,
        wikipedia_summary=detail.get("wikipedia_summary") or None,
        image_url=photo.get("medium_url") if photo else None,
        conservation_status=(
            detail["conservation_status"]["status_name"]
            if detail.get("conservation_status")
            else None
        ),
        vernaculars=extract_vernaculars(detail),
    )
