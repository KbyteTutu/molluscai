"""
Match an auction listing's `name` field to the most likely WoRMS taxon record.

Flow:
  1. Clean the noisy auction name string (drop variant suffixes, authorities, sp./aff./var. markers).
  2. Run hybrid_search with the cleaned name.
  3. Compute confidence from pg_trgm similarity between cleaned name and top-1 scientificname.
  4. If top-1 is unaccepted, also surface its accepted synonym via valid_aphia_id.
"""
from __future__ import annotations

import logging
import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.taxon import TaxonRead
from app.services.taxa_search import hybrid_search

log = logging.getLogger(__name__)

_VARIANT_MARKERS = ("sp.", "spp.", "aff.", "cf.", "var.", "subsp.", "f.")
_NOISE_RE = re.compile(r"\s+")


class TaxonMatchResponse(BaseModel):
    cleaned_query: str
    raw_name: str
    matched: Optional[TaxonRead] = None
    accepted: Optional[TaxonRead] = None
    alternatives: list[TaxonRead] = []
    confidence: str = "none"
    similarity: float = 0.0
    reason: Optional[str] = None


def normalize_auction_name(raw: str) -> str:
    """Strip cosmetic suffixes, authority parentheticals, and variant markers."""
    if not raw:
        return ""
    s = raw

    if " - " in s:
        s = s.split(" - ", 1)[0]

    if "," in s:
        s = s.split(",", 1)[0]

    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"†|‡", "", s)
    s = _NOISE_RE.sub(" ", s).strip()

    parts = s.split()
    cleaned: list[str] = []
    for p in parts:
        low = p.lower()
        if any(low == m or low == m.rstrip(".") for m in _VARIANT_MARKERS):
            break
        cleaned.append(p)
    if not cleaned:
        return ""

    if len(cleaned) >= 2 and cleaned[0][:1].isupper() and cleaned[1][:1].islower():
        return " ".join(cleaned[:2])
    return cleaned[0]


def _confidence_from_similarity(s: float) -> str:
    if s >= 0.85: return "high"
    if s >= 0.55: return "medium"
    if s >= 0.30: return "low"
    return "none"


async def _trgm_similarity(db: AsyncSession, a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    row = (await db.execute(
        text("SELECT similarity(:a, :b) AS sim"),
        {"a": a, "b": b},
    )).fetchone()
    return float(row.sim) if row else 0.0


async def match_auction_taxon(*, db: AsyncSession, user_id: Optional[UUID],
                              raw_name: str) -> TaxonMatchResponse:
    cleaned = normalize_auction_name(raw_name)
    if not cleaned:
        return TaxonMatchResponse(
            cleaned_query="", raw_name=raw_name,
            confidence="none", reason="名称为空或全部为变体标记，无法匹配",
        )

    try:
        result = await hybrid_search(
            db=db, user_id=user_id, q=cleaned,
            rank=None, family=None, genus=None,
            offset=0, limit=5,
        )
    except Exception as e:
        log.warning("hybrid search failed for auction match %r: %s", cleaned, e)
        return TaxonMatchResponse(
            cleaned_query=cleaned, raw_name=raw_name,
            confidence="none", reason=f"检索失败: {e}",
        )

    if not result.items:
        return TaxonMatchResponse(
            cleaned_query=cleaned, raw_name=raw_name,
            confidence="none", reason="未找到匹配的物种",
        )

    top = result.items[0]
    sim = await _trgm_similarity(db, cleaned, top.scientificname)
    confidence = _confidence_from_similarity(sim)

    accepted: Optional[TaxonRead] = None
    if top.status and top.status.lower() != "accepted" and top.valid_aphia_id and top.valid_aphia_id != top.aphia_id:
        accepted_rows = (await db.execute(
            text("""SELECT aphia_id, scientificname, authority, rank, status,
                           valid_aphia_id, valid_name,
                           kingdom, phylum, subphylum, class, subclass, infraclass,
                           superorder, "order", suborder, infraorder, superfamily,
                           family, genus, species_epithet,
                           is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct,
                           citation, url, data_source, last_synced_at
                    FROM taxa WHERE aphia_id = :id"""),
            {"id": top.valid_aphia_id},
        )).fetchall()
        if accepted_rows:
            accepted = TaxonRead.model_validate(dict(accepted_rows[0]._mapping))

    return TaxonMatchResponse(
        cleaned_query=cleaned,
        raw_name=raw_name,
        matched=top,
        accepted=accepted,
        alternatives=result.items[1:],
        confidence=confidence,
        similarity=round(sim, 4),
    )
