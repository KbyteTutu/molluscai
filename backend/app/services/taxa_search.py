"""
Hybrid taxa search: lexical (pg_trgm) + vector (pgvector) fused by RRF,
optionally reranked by a cross-encoder.

Lexical pool searches three sources and resolves every match to an accepted
taxon's aphia_id, with provenance annotation:
    * taxa.scientificname           -> kind="name"
    * taxa_synonyms.scientificname  -> kind="synonym"      (resolves to parent aphia_id)
    * taxa_vernaculars.vernacular   -> kind="vernacular"   (resolves to parent aphia_id)

Match priority on dedup: name > synonym > vernacular.

RRF (Reciprocal Rank Fusion) is parameter-free and robust against differing
score distributions between lexical trgm similarity and cosine distance.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.taxon import TaxonMatchInfo, TaxonRead, TaxonSearchResponse
from app.services.llm_providers import (
    compose_taxon_text,
    get_embedding_provider,
    get_rerank_provider,
    pad_or_truncate,
)

log = logging.getLogger(__name__)

LEXICAL_K = 50
VECTOR_K = 50
RRF_K = 60
RERANK_CANDIDATES = 30

MATCH_PRIORITY = {"name": 0, "synonym": 1, "vernacular": 2}


async def _pick_active(db: AsyncSession, purpose: str) -> Optional[dict]:
    row = (await db.execute(
        text("""SELECT id, model_name, provider, api_key, base_url, model_id,
                       price_input, price_unit
                FROM model_configs
                WHERE purpose = :p AND is_active = true
                ORDER BY id DESC LIMIT 1"""),
        {"p": purpose},
    )).fetchone()
    return dict(row._mapping) if row else None


async def _log_usage(db: AsyncSession, *, cfg_id: int, model_name: str, purpose: str,
                     user_id: Optional[UUID], input_tokens: int, latency_ms: int,
                     cost: Decimal, status: str = "success",
                     error: Optional[str] = None) -> None:
    await db.execute(
        text("""INSERT INTO model_usage_logs
                  (model_config_id, model_name, purpose, user_id, input_tokens,
                   cost, latency_ms, status, error_message)
                VALUES (:cfg_id, :model, :purpose, :uid, :tok, :cost, :lat, :st, :err)"""),
        {
            "cfg_id": cfg_id, "model": model_name, "purpose": purpose, "uid": user_id,
            "tok": input_tokens, "cost": cost, "lat": latency_ms,
            "st": status, "err": error,
        },
    )


def _cost(input_tokens: int, price: Optional[Decimal], unit: str) -> Decimal:
    if not price:
        return Decimal("0")
    if unit == "per_1k_tokens":
        return (Decimal(input_tokens) / Decimal(1000)) * price
    if unit == "per_1m_tokens":
        return (Decimal(input_tokens) / Decimal(1_000_000)) * price
    return Decimal("0")


async def _lexical_with_match(
    db: AsyncSession,
    q: str,
    rank: Optional[str],
    family: Optional[str],
    genus: Optional[str],
    status: Optional[str] = None,
) -> list[tuple[int, dict[str, Any]]]:
    qlike = f"{q}%"
    rank_clause = "AND t.rank = :rank" if rank else ""
    family_clause = "AND t.family ILIKE :family" if family else ""
    genus_clause = "AND t.genus ILIKE :genus" if genus else ""
    status_clause = "AND t.status = :status" if status else ""

    params: dict[str, Any] = {"q": q, "qlike": qlike, "lim": LEXICAL_K}
    if rank:
        params["rank"] = rank
    if family:
        params["family"] = f"{family}%"
    if genus:
        params["genus"] = f"{genus}%"
    if status:
        params["status"] = status

    name_rows = (await db.execute(
        text(f"""
            SELECT t.aphia_id, t.scientificname AS term, t.authority,
                   similarity(t.scientificname, :q) AS sim, t.status
            FROM taxa t
            WHERE (t.scientificname ILIKE :qlike OR t.scientificname % :q)
              {rank_clause} {family_clause} {genus_clause} {status_clause}
            ORDER BY sim DESC
            LIMIT :lim
        """),
        params,
    )).fetchall()

    syn_rows = (await db.execute(
        text(f"""
            SELECT t.aphia_id, s.scientificname AS term, s.authority,
                   similarity(s.scientificname, :q) AS sim, t.status
            FROM taxa_synonyms s
            JOIN taxa t ON t.aphia_id = s.aphia_id
            WHERE (s.scientificname ILIKE :qlike OR s.scientificname % :q)
              {rank_clause} {family_clause} {genus_clause} {status_clause}
            ORDER BY sim DESC
            LIMIT :lim
        """),
        params,
    )).fetchall()

    vern_rows = (await db.execute(
        text(f"""
            SELECT t.aphia_id, v.vernacular AS term, v.language_code,
                   similarity(v.vernacular, :q) AS sim, t.status
            FROM taxa_vernaculars v
            JOIN taxa t ON t.aphia_id = v.aphia_id
            WHERE (v.vernacular ILIKE :qlike OR v.vernacular % :q)
              {rank_clause} {family_clause} {genus_clause} {status_clause}
            ORDER BY sim DESC
            LIMIT :lim
        """),
        params,
    )).fetchall()

    by_aphia: dict[int, tuple[float, str, dict[str, Any]]] = {}

    def _consider(aid: int, sim: float, taxon_status: str, info: dict[str, Any]) -> None:
        existing = by_aphia.get(aid)
        if existing is None:
            by_aphia[aid] = (sim, taxon_status or "", info)
            return
        old_sim, _, old_info = existing
        old_pri = MATCH_PRIORITY[old_info["kind"]]
        new_pri = MATCH_PRIORITY[info["kind"]]
        if new_pri < old_pri or (new_pri == old_pri and sim > old_sim):
            by_aphia[aid] = (sim, taxon_status or "", info)

    for r in name_rows:
        _consider(int(r[0]), float(r[3] or 0.0), r[4] or "",
                  {"kind": "name", "term": r[1], "authority": r[2]})
    for r in syn_rows:
        _consider(int(r[0]), float(r[3] or 0.0), r[4] or "",
                  {"kind": "synonym", "term": r[1], "authority": r[2]})
    for r in vern_rows:
        _consider(int(r[0]), float(r[3] or 0.0), r[4] or "",
                  {"kind": "vernacular", "term": r[1], "language": r[2]})

    return sorted(
        ((aid, info) for aid, (_sim, _st, info) in by_aphia.items()),
        key=lambda kv: (0 if by_aphia[kv[0]][1] == "accepted" else 1, -by_aphia[kv[0]][0]),
    )


async def _lexical_ids(db: AsyncSession, q: str, rank: Optional[str],
                       family: Optional[str], genus: Optional[str],
                       status: Optional[str] = None) -> list[int]:
    pairs = await _lexical_with_match(db, q, rank, family, genus, status)
    return [aid for aid, _ in pairs]


async def _vector_ids(db: AsyncSession, model_name: str, query_vec: list[float],
                      rank: Optional[str], family: Optional[str],
                      genus: Optional[str]) -> list[int]:
    vec_literal = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"
    clauses = ["e.model_name = :model"]
    params: dict = {"model": model_name, "q": vec_literal, "lim": VECTOR_K}
    if rank:
        clauses.append("t.rank = :rank"); params["rank"] = rank
    if family:
        clauses.append("t.family ILIKE :family"); params["family"] = f"{family}%"
    if genus:
        clauses.append("t.genus ILIKE :genus"); params["genus"] = f"{genus}%"
    where = " AND ".join(clauses)
    rows = (await db.execute(
        text(f"""SELECT e.aphia_id
                 FROM taxa_embeddings e
                 JOIN taxa t ON t.aphia_id = e.aphia_id
                 WHERE {where}
                 ORDER BY e.embedding <=> CAST(:q AS halfvec)
                 LIMIT :lim"""),
        params,
    )).fetchall()
    return [int(r[0]) for r in rows]


def _rrf_fuse(lexical: list[int], vector: list[int], k: int = RRF_K) -> list[int]:
    scores: dict[int, float] = {}
    for rank, aid in enumerate(lexical):
        scores[aid] = scores.get(aid, 0.0) + 1.0 / (k + rank + 1)
    for rank, aid in enumerate(vector):
        scores[aid] = scores.get(aid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda a: scores[a], reverse=True)


async def _load_taxa(db: AsyncSession, aphia_ids: list[int]) -> dict[int, dict]:
    if not aphia_ids:
        return {}
    rows = (await db.execute(
        text("""SELECT aphia_id, scientificname, authority, rank, status,
                       valid_aphia_id, valid_name,
                       kingdom, phylum, subphylum, class, subclass, infraclass,
                       superorder, "order", suborder, infraorder, superfamily,
                       family, genus, species_epithet,
                       is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct,
                       citation, url, data_source, last_synced_at
                FROM taxa WHERE aphia_id = ANY(:ids)"""),
        {"ids": aphia_ids},
    )).fetchall()
    return {int(r._mapping["aphia_id"]): dict(r._mapping) for r in rows}


def _attach_match(item: dict, match_map: dict[int, dict[str, Any]]) -> dict:
    info = match_map.get(int(item["aphia_id"]))
    if info is None:
        return item
    return {**item, "match_info": TaxonMatchInfo(**info)}


async def lexical_search(*, db: AsyncSession, q: str,
                         rank: Optional[str], family: Optional[str], genus: Optional[str],
                         status: Optional[str] = None,
                         offset: int, limit: int) -> TaxonSearchResponse:
    pairs = await _lexical_with_match(db, q, rank, family, genus, status)
    ids = [aid for aid, _ in pairs]
    match_map = {aid: info for aid, info in pairs}
    pool = await _load_taxa(db, ids)
    items = [_attach_match(pool[i], match_map) for i in ids if i in pool][offset: offset + limit]
    return TaxonSearchResponse(
        items=[TaxonRead.model_validate(i) for i in items],
        total=len(ids), offset=offset, limit=limit,
    )


async def hybrid_search(*, db: AsyncSession, user_id: Optional[UUID], q: str,
                        rank: Optional[str], family: Optional[str], genus: Optional[str],
                        status: Optional[str] = None,
                        offset: int, limit: int) -> TaxonSearchResponse:
    emb_cfg = await _pick_active(db, "embedding")
    if emb_cfg is None:
        log.info("hybrid requested but no active embedding model; falling back to lexical")
        pairs = await _lexical_with_match(db, q, rank, family, genus, status)
        ids = [aid for aid, _ in pairs]
        match_map = {aid: info for aid, info in pairs}
        pool = await _load_taxa(db, ids)
        items = [_attach_match(pool[i], match_map) for i in ids if i in pool][offset: offset + limit]
        return TaxonSearchResponse(
            items=[TaxonRead.model_validate(i) for i in items],
            total=len(ids), offset=offset, limit=limit,
        )

    provider = get_embedding_provider(
        emb_cfg["provider"], emb_cfg["base_url"] or "",
        emb_cfg["api_key"], emb_cfg["model_id"] or emb_cfg["model_name"],
    )
    try:
        er = await provider.embed([q])
    except Exception as e:
        log.warning("embed query failed: %s; falling back to lexical", e)
        await _log_usage(db, cfg_id=emb_cfg["id"], model_name=emb_cfg["model_name"],
                         purpose="embedding", user_id=user_id, input_tokens=0,
                         latency_ms=0, cost=Decimal("0"), status="error", error=str(e)[:300])
        await db.commit()
        pairs = await _lexical_with_match(db, q, rank, family, genus, status)
        ids = [aid for aid, _ in pairs]
        match_map = {aid: info for aid, info in pairs}
        pool = await _load_taxa(db, ids)
        items = [_attach_match(pool[i], match_map) for i in ids if i in pool][offset: offset + limit]
        return TaxonSearchResponse(
            items=[TaxonRead.model_validate(i) for i in items],
            total=len(ids), offset=offset, limit=limit,
        )

    qvec = pad_or_truncate(er.vectors[0], 2000)
    await _log_usage(db, cfg_id=emb_cfg["id"], model_name=emb_cfg["model_name"],
                     purpose="embedding", user_id=user_id,
                     input_tokens=er.input_tokens, latency_ms=er.latency_ms,
                     cost=_cost(er.input_tokens, emb_cfg.get("price_input"),
                                emb_cfg.get("price_unit") or "per_1k_tokens"))

    lex_pairs = await _lexical_with_match(db, q, rank, family, genus, status)
    lex_ids = [aid for aid, _ in lex_pairs]
    match_map = {aid: info for aid, info in lex_pairs}
    vec_ids = await _vector_ids(db, emb_cfg["model_name"], qvec, rank, family, genus)
    fused = _rrf_fuse(lex_ids, vec_ids)[:RERANK_CANDIDATES]
    pool = await _load_taxa(db, fused)

    rer_cfg = await _pick_active(db, "rerank")
    if rer_cfg and fused:
        candidates = [pool[i] for i in fused if i in pool]
        docs = [compose_taxon_text(c) for c in candidates]
        try:
            rprov = get_rerank_provider(
                rer_cfg["provider"], rer_cfg["base_url"] or "",
                rer_cfg["api_key"], rer_cfg["model_id"] or rer_cfg["model_name"],
            )
            rr = await rprov.rerank(q, docs, top_n=min(len(docs), offset + limit))
            await _log_usage(db, cfg_id=rer_cfg["id"], model_name=rer_cfg["model_name"],
                             purpose="rerank", user_id=user_id,
                             input_tokens=rr.input_tokens, latency_ms=rr.latency_ms,
                             cost=_cost(rr.input_tokens, rer_cfg.get("price_input"),
                                        rer_cfg.get("price_unit") or "per_1k_tokens"))
            ordered = [candidates[h.index] for h in rr.hits if 0 <= h.index < len(candidates)]
        except Exception as e:
            log.warning("rerank failed: %s; using RRF order", e)
            await _log_usage(db, cfg_id=rer_cfg["id"], model_name=rer_cfg["model_name"],
                             purpose="rerank", user_id=user_id, input_tokens=0,
                             latency_ms=0, cost=Decimal("0"),
                             status="error", error=str(e)[:300])
            ordered = candidates
    else:
        ordered = [pool[i] for i in fused if i in pool]

    total = len(ordered)
    page = [_attach_match(item, match_map) for item in ordered[offset: offset + limit]]
    await db.commit()
    return TaxonSearchResponse(
        items=[TaxonRead.model_validate(i) for i in page],
        total=total, offset=offset, limit=limit,
    )
