"""
Auction search: lexical (pg_trgm), vector (pgvector), and hybrid (RRF fusion).
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple, List
from uuid import UUID

from sqlalchemy import func, select, text, Numeric
from sqlalchemy import case as sa_case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auction import Auction
from app.schemas.auction import AuctionRead, AuctionSearchRequest
from app.services.llm_providers import (
    get_embedding_provider,
    pad_or_truncate,
)

log = logging.getLogger(__name__)

LEXICAL_K = 50
VECTOR_K = 50
RRF_K = 60
HYBRID_CANDIDATES = 30


def _build_conditions(filters: AuctionSearchRequest) -> list:
    conditions = []

    if filters.name:
        conditions.append(
            func.similarity(Auction.name, filters.name) > 0.1
        )
    if filters.family:
        conditions.append(Auction.family.ilike(f"%{filters.family}%"))
    if filters.locality:
        conditions.append(
            func.similarity(Auction.locality, filters.locality) > 0.1
        )
    if filters.size:
        conditions.append(Auction.size.ilike(f"%{filters.size}%"))
    if filters.size_min is not None or filters.size_max is not None or filters.has_no_size:
        size_num = sa_case(
            (Auction.size.op("~")("^\\d"),
             func.cast(func.regexp_replace(Auction.size, r"^(\d+(?:\.\d+)?).*", r"\1"), Numeric)),
            else_=None,
        )
        if filters.has_no_size:
            conditions.append(func.coalesce(size_num, -1) == -1)
        else:
            conditions.append(size_num.isnot(None))
            if filters.size_min is not None:
                conditions.append(size_num >= filters.size_min)
            if filters.size_max is not None:
                conditions.append(size_num <= filters.size_max)
    if filters.price_min is not None:
        conditions.append(Auction.final_price >= filters.price_min)
    if filters.price_max is not None:
        conditions.append(Auction.final_price <= filters.price_max)
    if filters.is_sold is not None:
        conditions.append(Auction.is_sold == filters.is_sold)
    if filters.seller:
        conditions.append(Auction.seller.ilike(f"%{filters.seller}%"))
    if filters.end_date_from:
        conditions.append(Auction.end_date >= filters.end_date_from)
    if filters.end_date_to:
        conditions.append(Auction.end_date <= filters.end_date_to)

    return conditions


def _build_condition_text(filters: AuctionSearchRequest) -> tuple[str, dict]:
    clauses = []
    params: dict = {}

    if filters.name:
        clauses.append("similarity(a.name, :name) > 0.1")
        params["name"] = filters.name
    if filters.family:
        clauses.append("a.family ILIKE :family")
        params["family"] = f"%{filters.family}%"
    if filters.locality:
        clauses.append("similarity(a.locality, :locality) > 0.1")
        params["locality"] = filters.locality
    if filters.size:
        clauses.append("a.size ILIKE :size")
        params["size"] = f"%{filters.size}%"
    if filters.size_min is not None or filters.size_max is not None or filters.has_no_size:
        size_expr = (
            "CASE WHEN a.size ~ '^\\d' "
            "THEN CAST(regexp_replace(a.size, '^(\\d+(?:\\.\\d+)?).*', '\\1') AS numeric) "
            "ELSE NULL END"
        )
        if filters.has_no_size:
            clauses.append(f"COALESCE({size_expr}, -1) = -1")
        else:
            clauses.append(f"{size_expr} IS NOT NULL")
            if filters.size_min is not None:
                clauses.append(f"{size_expr} >= :size_min")
                params["size_min"] = filters.size_min
            if filters.size_max is not None:
                clauses.append(f"{size_expr} <= :size_max")
                params["size_max"] = filters.size_max
    if filters.price_min is not None:
        clauses.append("a.final_price >= :price_min")
        params["price_min"] = filters.price_min
    if filters.price_max is not None:
        clauses.append("a.final_price <= :price_max")
        params["price_max"] = filters.price_max
    if filters.is_sold is not None:
        clauses.append("a.is_sold = :is_sold")
        params["is_sold"] = filters.is_sold
    if filters.seller:
        clauses.append("a.seller ILIKE :seller")
        params["seller"] = f"%{filters.seller}%"
    if filters.end_date_from:
        clauses.append("a.end_date >= :end_date_from")
        params["end_date_from"] = filters.end_date_from
    if filters.end_date_to:
        clauses.append("a.end_date <= :end_date_to")
        params["end_date_to"] = filters.end_date_to

    where = " AND ".join(clauses) if clauses else "TRUE"
    return where, params


def _sort_columns(filters: AuctionSearchRequest) -> list:
    sort_map = {
        "price_desc":   [Auction.final_price.desc().nullslast()],
        "price_asc":    [Auction.final_price.asc().nullslast()],
        "item_no_desc": [Auction.item_no.desc()],
        "end_date_desc":[Auction.end_date.desc().nullslast()],
        "relevance": [
            func.similarity(Auction.name, filters.name).desc(),
            Auction.end_date.desc().nullslast(),
        ] if filters.name else [Auction.end_date.desc().nullslast()],
    }
    return sort_map.get(filters.sort or "relevance", sort_map["end_date_desc"])


def _sort_text(filters: AuctionSearchRequest) -> str:
    if filters.name:
        return f"similarity(a.name, :name) DESC, a.end_date DESC NULLS LAST"
    return "a.end_date DESC NULLS LAST"


async def _lexical_ids(
    db: AsyncSession, conditions: list, filters: AuctionSearchRequest
) -> List[int]:
    order_cols = _sort_columns(filters)
    stmt = select(Auction.item_no)
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.order_by(*order_cols).limit(LEXICAL_K)
    rows = await db.execute(stmt)
    return [r[0] for r in rows]


async def _vector_ids(
    db: AsyncSession, model_name: str, query_vec: list[float],
    filters: AuctionSearchRequest,
) -> List[int]:
    vec_literal = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"
    where, params = _build_condition_text(filters)
    params["model"] = model_name
    params["q"] = vec_literal
    params["lim"] = VECTOR_K

    rows = await db.execute(
        text(f"""SELECT e.item_no
                 FROM auction_embeddings e
                 JOIN auctions a ON a.item_no = e.item_no
                 WHERE e.model_name = :model AND ({where})
                 ORDER BY e.embedding <=> CAST(:q AS halfvec)
                 LIMIT :lim"""),
        params,
    )
    return [int(r[0]) for r in rows]


async def _load_by_item_nos(db: AsyncSession, item_nos: list[int]) -> list[Auction]:
    if not item_nos:
        return []
    stmt = select(Auction).where(Auction.item_no.in_(item_nos))
    rows = await db.execute(stmt)
    all_items = rows.scalars().all()
    by_item_no = {a.item_no: a for a in all_items}
    return [by_item_no[no] for no in item_nos if no in by_item_no]


def _rrf_fuse(lexical: list[int], vector: list[int], k: int = RRF_K) -> list[int]:
    scores: dict[int, float] = {}
    for rank, item_no in enumerate(lexical):
        scores[item_no] = scores.get(item_no, 0.0) + 1.0 / (k + rank + 1)
    for rank, item_no in enumerate(vector):
        scores[item_no] = scores.get(item_no, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda a: scores[a], reverse=True)


async def search_auctions(
    db: AsyncSession, filters: AuctionSearchRequest, *,
    mode: str = "lexical", user_id: Optional[UUID] = None,
) -> Tuple[List[Auction], int]:
    conditions = _build_conditions(filters)

    if mode == "lexical" or (mode != "vector" and mode != "hybrid"):
        return await _lexical_search(db, conditions, filters)

    emb_cfg = await _pick_active(db, "embedding")
    if emb_cfg is None:
        log.info("vector/hybrid requested but no active embedding model; falling back to lexical")
        return await _lexical_search(db, conditions, filters)

    provider = get_embedding_provider(
        emb_cfg["provider"], emb_cfg["base_url"] or "",
        emb_cfg["api_key"], emb_cfg["model_id"] or emb_cfg["model_name"],
    )
    try:
        query_text = filters.name or ""
        er = await provider.embed([query_text])
    except Exception as e:
        log.warning("embed query failed: %s; falling back to lexical", e)
        return await _lexical_search(db, conditions, filters)

    qvec = pad_or_truncate(er.vectors[0], 2000)

    if mode == "vector":
        vec_ids = await _vector_ids(db, emb_cfg["model_name"], qvec, filters)
        items = await _load_by_item_nos(db, vec_ids)
        total = len(items)
        page = items[filters.offset: filters.offset + filters.limit]
        return page, total

    # hybrid mode: RRF fuse lexical + vector
    lex_ids = await _lexical_ids(db, conditions, filters)
    vec_ids = await _vector_ids(db, emb_cfg["model_name"], qvec, filters)
    fused = _rrf_fuse(lex_ids, vec_ids)[:HYBRID_CANDIDATES]
    items = await _load_by_item_nos(db, fused)
    total = len(items)
    page = items[filters.offset: filters.offset + filters.limit]
    return page, total


async def get_auction_by_item_no(
    db: AsyncSession, item_no: int
) -> Optional[Auction]:
    result = await db.execute(
        select(Auction).where(Auction.item_no == item_no)
    )
    return result.scalar_one_or_none()


async def _lexical_search(
    db: AsyncSession, conditions: list, filters: AuctionSearchRequest,
) -> Tuple[List[Auction], int]:
    base_query = select(Auction)
    if conditions:
        base_query = base_query.where(*conditions)

    order_cols = _sort_columns(filters)
    query = base_query.order_by(*order_cols).offset(filters.offset).limit(filters.limit)
    result = await db.execute(query)
    items = result.scalars().all()

    total = filters.offset + len(items) + 1 if len(items) == filters.limit else filters.offset + len(items)

    return items, total


async def _pick_active(db: AsyncSession, purpose: str) -> Optional[dict]:
    from app.models.model_config import ModelConfig
    row = await db.execute(
        select(
            ModelConfig.id, ModelConfig.model_name, ModelConfig.provider,
            ModelConfig.base_url, ModelConfig.api_key, ModelConfig.model_id,
            ModelConfig.price_input, ModelConfig.price_unit,
        ).where(
            ModelConfig.purpose == purpose,
            ModelConfig.is_active == True,
        )
    )
    r = row.first()
    if r is None:
        return None
    return {
        "id": r[0], "model_name": r[1], "provider": r[2],
        "base_url": r[3], "api_key": r[4], "model_id": r[5],
        "price_input": r[6], "price_unit": r[7],
    }
