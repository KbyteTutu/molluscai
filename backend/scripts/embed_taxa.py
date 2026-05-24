"""
Batch-embed taxa using the currently active embedding ModelConfig.

Invoked via:
  docker compose exec backend python -m scripts.embed_taxa
  docker compose exec backend python -m scripts.embed_taxa --rebuild
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from decimal import Decimal
from typing import Any, Optional

import asyncpg

from app.config import settings
from app.services.llm_providers import (
    compose_taxon_text,
    get_embedding_provider,
    pad_or_truncate,
    text_hash,
)

import signal

has_service = False
EmbeddingTaskService: Any = None
try:
    from app.services.embedding_task_service import EmbeddingTaskService as _EmbeddingTaskService
    EmbeddingTaskService = _EmbeddingTaskService  # type: ignore[reportConstantRedefinition]
    has_service = True
except ImportError:
    pass

log = logging.getLogger("embed_taxa")

BATCH_SIZE = 64
CONCURRENCY = 6

_cancel_event: Optional[asyncio.Event] = None


def request_cancel():
    if _cancel_event:
        _cancel_event.set()


async def pick_active_embedding_config(conn: asyncpg.Connection) -> Optional[dict]:
    row = await conn.fetchrow(
        """SELECT id, model_name, provider, api_key, base_url, model_id,
                  price_input, price_unit
           FROM model_configs
           WHERE purpose = 'embedding' AND is_active = true
           ORDER BY id DESC LIMIT 1"""
    )
    return dict(row) if row else None


async def pick_batches(conn: asyncpg.Connection, model_name: str,
                       total_needed: int, after_id: Optional[int] = None) -> list[list[dict]]:
    if after_id is not None:
        rows = await conn.fetch(
            """SELECT t.aphia_id, t.scientificname, t.authority, t.rank,
                      t.kingdom, t.phylum, t.class, t."order", t.family, t.genus,
                      t.species_epithet,
                      t.is_marine, t.is_brackish, t.is_freshwater,
                      t.is_terrestrial, t.is_extinct
               FROM taxa t
               LEFT JOIN taxa_embeddings e
                 ON e.aphia_id = t.aphia_id AND e.model_name = $1
               WHERE e.aphia_id IS NULL AND t.aphia_id > $3
               ORDER BY t.aphia_id LIMIT $2""",
            model_name, total_needed, after_id,
        )
    else:
        rows = await conn.fetch(
            """SELECT t.aphia_id, t.scientificname, t.authority, t.rank,
                      t.kingdom, t.phylum, t.class, t."order", t.family, t.genus,
                      t.species_epithet,
                      t.is_marine, t.is_brackish, t.is_freshwater,
                      t.is_terrestrial, t.is_extinct
               FROM taxa t
               LEFT JOIN taxa_embeddings e
                 ON e.aphia_id = t.aphia_id AND e.model_name = $1
               WHERE e.aphia_id IS NULL
               ORDER BY t.aphia_id LIMIT $2""",
            model_name, total_needed,
        )
    all_rows = [dict(r) for r in rows]
    return [all_rows[i:i + BATCH_SIZE] for i in range(0, len(all_rows), BATCH_SIZE)]


async def upsert_batch(conn: asyncpg.Connection, *, model_name: str, dim: int,
                       items: list[tuple[int, list[float], str]]) -> None:
    await conn.executemany(
        """INSERT INTO taxa_embeddings (aphia_id, model_name, dim, embedding, text_hash)
           VALUES ($1, $2, $3, $4::halfvec, $5)
           ON CONFLICT (aphia_id, model_name) DO UPDATE
           SET dim = EXCLUDED.dim, embedding = EXCLUDED.embedding,
               text_hash = EXCLUDED.text_hash, created_at = now()""",
        [(aid, model_name, dim, "[" + ",".join(f"{v:.6f}" for v in vec) + "]", h)
         for aid, vec, h in items],
    )


async def log_usage(conn: asyncpg.Connection, cfg_id: int, model_name: str,
                    input_tokens: int, latency_ms: int, cost: Decimal) -> None:
    await conn.execute(
        """INSERT INTO model_usage_logs
             (model_config_id, model_name, purpose, input_tokens, cost, latency_ms, status)
           VALUES ($1, $2, 'embedding', $3, $4, $5, 'success')""",
        cfg_id, model_name, input_tokens, cost, latency_ms,
    )


def compute_cost(input_tokens: int, price_input: Optional[Decimal],
                 price_unit: str) -> Decimal:
    if not price_input:
        return Decimal("0")
    if price_unit == "per_1k_tokens":
        return (Decimal(input_tokens) / Decimal(1000)) * price_input
    if price_unit == "per_1m_tokens":
        return (Decimal(input_tokens) / Decimal(1_000_000)) * price_input
    return Decimal("0")


async def process_batch(conn: asyncpg.Connection, cfg: dict, rows: list[dict],
                        sem: asyncio.Semaphore) -> int:
    async with sem:
        if _cancel_event and _cancel_event.is_set():
            return 0
        provider = get_embedding_provider(
            cfg["provider"], cfg["base_url"] or "", cfg["api_key"],
            cfg["model_id"] or cfg["model_name"],
        )
        texts = [compose_taxon_text(r) for r in rows]
        hashes = [text_hash(t) for t in texts]
        result = await provider.embed(texts)

        items = [
            (row["aphia_id"], pad_or_truncate(vec, 2000), h)
            for row, vec, h in zip(rows, result.vectors, hashes, strict=True)
        ]
        await upsert_batch(conn, model_name=cfg["model_name"], dim=len(result.vectors[0]), items=items)

        cost = compute_cost(
            result.input_tokens, cfg.get("price_input"),
            cfg.get("price_unit") or "per_1k_tokens",
        )
        await log_usage(
            conn, cfg["id"], cfg["model_name"],
            input_tokens=result.input_tokens, latency_ms=result.latency_ms, cost=cost,
        )
        return len(rows)


async def run(rebuild: bool, max_rows: Optional[int], task_db_id: Optional[int] = None) -> int:
    global _cancel_event
    _cancel_event = asyncio.Event()

    # --- graceful shutdown handler ---
    _shutdown_requested = False

    def _handle_signal(signum, frame):
        nonlocal _shutdown_requested
        if not _shutdown_requested:
            _shutdown_requested = True
            log.warning("Received signal %s, initiating graceful shutdown...", signum)
            if _cancel_event:
                _cancel_event.set()
            _shutdown_requested = True

    # Register handlers
    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGTERM, lambda: _handle_signal(signal.SIGTERM, None))
        loop.add_signal_handler(signal.SIGINT, lambda: _handle_signal(signal.SIGINT, None))
    except NotImplementedError:
        # Windows or non-main-thread — fall back to signal module
        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)
    # --- end graceful shutdown ---

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    pool = await asyncpg.create_pool(settings.DATABASE_URL_SYNC, min_size=2, max_size=CONCURRENCY + 2)
    try:
        async with pool.acquire() as conn:
            cfg = await pick_active_embedding_config(conn)
        if not cfg:
            log.error("no active embedding ModelConfig — configure one at /admin/models first")
            return 2
        log.info("model: %s  concurrency=%d  batch_size=%d",
                 cfg["model_name"], CONCURRENCY, BATCH_SIZE)

        if rebuild:
            log.warning("REBUILD: deleting existing embeddings for %s", cfg["model_name"])
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM taxa_embeddings WHERE model_name = $1", cfg["model_name"])

        sem = asyncio.Semaphore(CONCURRENCY)
        total_embedded = 0
        started = time.perf_counter()
        fetch_size = BATCH_SIZE * CONCURRENCY * 2

        checkpoint_id = None
        if task_db_id is not None and has_service:
            async with pool.acquire() as conn:
                checkpoint_id, total_embedded = await EmbeddingTaskService.get_checkpoint(conn, task_db_id)
            log.info("Resuming from checkpoint: aphia_id=%s, processed=%d", checkpoint_id, total_embedded)

        while not (_cancel_event and _cancel_event.is_set()):
            async with pool.acquire() as conn:
                batches = await pick_batches(conn, cfg["model_name"], fetch_size, after_id=checkpoint_id)
            if not batches:
                break

            async def _do_batch(batch):
                async with pool.acquire() as conn:
                    return await process_batch(conn, cfg, batch, sem)

            tasks = [_do_batch(b) for b in batches]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, BaseException):
                    log.error("batch error: %s", r)
                else:
                    total_embedded += r

            if task_db_id is not None and has_service and batches:
                max_id = max(int(row["aphia_id"]) for batch in batches for row in batch)
                checkpoint_id = max_id
                async with pool.acquire() as conn:
                    await EmbeddingTaskService.save_checkpoint(conn, task_db_id, checkpoint_id, total_embedded)

            elapsed = time.perf_counter() - started
            rate = total_embedded / max(elapsed, 0.001)
            log.info("progress: %d embedded  (%.1f/s  elapsed=%ds)",
                     total_embedded, rate, int(elapsed))

            if max_rows and total_embedded >= max_rows:
                break

        async with pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM taxa_embeddings WHERE model_name = $1", cfg["model_name"]
            )
        cancelled = _cancel_event.is_set() if _cancel_event else False
        log.info("done. total=%d for %s  (cancelled=%s)", total, cfg["model_name"], cancelled)

        if task_db_id is not None and has_service:
            async with pool.acquire() as conn:
                state = "cancelled" if (_cancel_event and _cancel_event.is_set()) else "completed"
                await EmbeddingTaskService.update_state(conn, task_db_id, state, total_count=total_embedded)

        return 0
    finally:
        await pool.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    return asyncio.run(run(rebuild=args.rebuild, max_rows=args.limit))


if __name__ == "__main__":
    sys.exit(main())
