import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Permission, RequirePermission, get_db
from app.models.user import User
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigRead,
    ModelConfigUpdate,
    ModelTestResponse,
    ModelUsageSummary,
    RecentUsageRow,
)
from app.services.llm_providers import (
    get_embedding_provider,
    get_rerank_provider,
)

log = logging.getLogger(__name__)

router = APIRouter()
require_admin = RequirePermission(Permission.MANAGE_USERS)

ALLOWED_PURPOSES = {"embedding", "rerank", "llm_chat", "ocr", "vision"}


def _serialize(row) -> dict:
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    key = d.get("api_key") or ""
    d["api_key_tail"] = f"…{key[-4:]}" if len(key) >= 4 else None
    d.pop("api_key", None)
    return d


@router.get("", response_model=list[ModelConfigRead])
async def list_models(
    purpose: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    sql = "SELECT id, model_name, provider, api_key, base_url, model_id, purpose, price_input, price_output, price_unit, is_active, created_at FROM model_configs"
    params: dict = {}
    if purpose:
        sql += " WHERE purpose = :purpose"
        params["purpose"] = purpose
    sql += " ORDER BY purpose, is_active DESC, model_name"
    rows = (await db.execute(text(sql), params)).fetchall()
    return [ModelConfigRead.model_validate(_serialize(r)) for r in rows]


@router.post("", response_model=ModelConfigRead, status_code=status.HTTP_201_CREATED)
async def create_model(
    payload: ModelConfigCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    if payload.purpose not in ALLOWED_PURPOSES:
        raise HTTPException(400, f"purpose must be one of {sorted(ALLOWED_PURPOSES)}")

    if payload.is_active and payload.purpose in {"embedding", "rerank"}:
        await db.execute(
            text("UPDATE model_configs SET is_active=false WHERE purpose = :p"),
            {"p": payload.purpose},
        )

    row = (await db.execute(
        text("""
            INSERT INTO model_configs
                (model_name, provider, api_key, base_url, model_id, purpose,
                 price_input, price_output, price_unit, is_active)
            VALUES (:model_name, :provider, :api_key, :base_url, :model_id, :purpose,
                    :price_input, :price_output, :price_unit, :is_active)
            RETURNING id, model_name, provider, api_key, base_url, model_id, purpose,
                      price_input, price_output, price_unit, is_active, created_at
        """),
        payload.model_dump(),
    )).fetchone()
    await db.commit()
    return ModelConfigRead.model_validate(_serialize(row))


@router.patch("/{cfg_id}", response_model=ModelConfigRead)
async def update_model(
    cfg_id: int,
    payload: ModelConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        row = (await db.execute(
            text("SELECT id, model_name, provider, api_key, base_url, model_id, purpose, price_input, price_output, price_unit, is_active, created_at FROM model_configs WHERE id = :id"),
            {"id": cfg_id},
        )).fetchone()
        if not row:
            raise HTTPException(404, "not found")
        return ModelConfigRead.model_validate(_serialize(row))

    if updates.get("is_active") is True:
        row = (await db.execute(
            text("SELECT purpose FROM model_configs WHERE id = :id"), {"id": cfg_id}
        )).fetchone()
        if row and row.purpose in {"embedding", "rerank"}:
            await db.execute(
                text("UPDATE model_configs SET is_active=false WHERE purpose = :p AND id != :id"),
                {"p": row.purpose, "id": cfg_id},
            )

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = cfg_id
    row = (await db.execute(
        text(f"""UPDATE model_configs SET {set_clause}
                 WHERE id = :id
                 RETURNING id, model_name, provider, api_key, base_url, model_id, purpose,
                           price_input, price_output, price_unit, is_active, created_at"""),
        updates,
    )).fetchone()
    await db.commit()
    if not row:
        raise HTTPException(404, "not found")
    return ModelConfigRead.model_validate(_serialize(row))


@router.delete("/{cfg_id}", status_code=204)
async def delete_model(
    cfg_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await db.execute(text("DELETE FROM model_configs WHERE id = :id"), {"id": cfg_id})
    await db.commit()


@router.post("/{cfg_id}/test", response_model=ModelTestResponse)
async def test_model(
    cfg_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = (await db.execute(
        text("""SELECT provider, api_key, base_url, model_id, purpose
                FROM model_configs WHERE id = :id"""),
        {"id": cfg_id},
    )).fetchone()
    if not row:
        raise HTTPException(404, "not found")

    try:
        if row.purpose == "embedding":
            provider = get_embedding_provider(
                row.provider, row.base_url or "", row.api_key, row.model_id or ""
            )
            result = await provider.embed(["Conus aurisiacus"])
            return ModelTestResponse(
                success=True,
                latency_ms=result.latency_ms,
                sample_dim=len(result.vectors[0]) if result.vectors else 0,
                message=f"OK · model={result.model_id} · tokens={result.input_tokens}",
            )
        elif row.purpose == "rerank":
            provider = get_rerank_provider(
                row.provider, row.base_url or "", row.api_key, row.model_id or ""
            )
            result = await provider.rerank(
                "cone snail",
                ["Conus aurisiacus Linnaeus 1758", "Cypraea tigris", "Murex pecten"],
                top_n=2,
            )
            return ModelTestResponse(
                success=True,
                latency_ms=result.latency_ms,
                message=f"OK · model={result.model_id} · top hit index={result.hits[0].index if result.hits else None}",
            )
        else:
            return ModelTestResponse(success=False, message=f"purpose {row.purpose} not testable yet")
    except Exception as e:
        log.warning("model test failed: %s", e)
        return ModelTestResponse(success=False, message=str(e)[:300])


@router.get("/usage/summary", response_model=list[ModelUsageSummary])
async def usage_summary(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(
        text("""
            SELECT
                model_config_id,
                model_name,
                purpose,
                COUNT(*) AS calls,
                COALESCE(SUM(input_tokens), 0)::INT AS input_tokens,
                COALESCE(SUM(input_tokens + COALESCE(output_tokens, 0)), 0)::INT AS total_tokens,
                COALESCE(SUM(cost), 0) AS cost,
                AVG(latency_ms)::INT AS avg_latency_ms
            FROM model_usage_logs
            WHERE created_at >= :since
            GROUP BY model_config_id, model_name, purpose
            ORDER BY cost DESC
        """),
        {"since": since},
    )).fetchall()
    return [ModelUsageSummary(**dict(r._mapping)) for r in rows]


@router.get("/usage/recent", response_model=list[RecentUsageRow])
async def usage_recent(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = (await db.execute(
        text("""
            SELECT id, model_name, purpose, input_tokens, cost, latency_ms,
                   status, error_message, created_at
            FROM model_usage_logs
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"limit": limit},
    )).fetchall()
    return [RecentUsageRow(**dict(r._mapping)) for r in rows]


@router.get("/embeddings/status")
async def embeddings_status(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    total_taxa = (await db.execute(text("SELECT COUNT(*) FROM taxa"))).scalar_one()

    active_emb = (await db.execute(text("""
        SELECT id, model_name, provider, model_id, base_url, price_input, price_unit
        FROM model_configs WHERE purpose='embedding' AND is_active=true
        ORDER BY id DESC LIMIT 1
    """))).fetchone()

    coverage_rows = (await db.execute(text("""
        SELECT model_name, COUNT(*)::int AS embedded,
               MAX(created_at) AS last_at,
               MIN(created_at) AS first_at
        FROM taxa_embeddings
        GROUP BY model_name
        ORDER BY embedded DESC
    """))).fetchall()

    throughput_1h = (await db.execute(text("""
        SELECT COUNT(*)::int AS calls,
               COALESCE(SUM(input_tokens),0)::int AS tokens,
               COALESCE(SUM(cost),0) AS cost,
               COUNT(*) FILTER (WHERE status='error')::int AS errors,
               AVG(latency_ms)::int AS avg_latency_ms
        FROM model_usage_logs
        WHERE purpose='embedding' AND created_at >= now() - INTERVAL '1 hour'
    """))).fetchone()

    throughput_24h = (await db.execute(text("""
        SELECT COUNT(*)::int AS calls,
               COALESCE(SUM(input_tokens),0)::int AS tokens,
               COALESCE(SUM(cost),0) AS cost,
               COUNT(*) FILTER (WHERE status='error')::int AS errors,
               AVG(latency_ms)::int AS avg_latency_ms
        FROM model_usage_logs
        WHERE purpose='embedding' AND created_at >= now() - INTERVAL '24 hours'
    """))).fetchone()

    recent_errors = (await db.execute(text("""
        SELECT id, model_name, error_message, created_at
        FROM model_usage_logs
        WHERE purpose='embedding' AND status='error'
        ORDER BY created_at DESC LIMIT 5
    """))).fetchall()

    coverage = []
    for r in coverage_rows:
        m = dict(r._mapping)
        m["pct"] = round((m["embedded"] / total_taxa) * 100, 2) if total_taxa else 0
        coverage.append(m)

    return {
        "total_taxa": total_taxa,
        "active_model": dict(active_emb._mapping) if active_emb else None,
        "coverage": coverage,
        "throughput_1h": dict(throughput_1h._mapping),
        "throughput_24h": dict(throughput_24h._mapping),
        "recent_errors": [dict(r._mapping) for r in recent_errors],
    }
