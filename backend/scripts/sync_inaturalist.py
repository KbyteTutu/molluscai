"""
Batch-sync iNaturalist metadata and vernacular names for taxa.

Usage:
  docker compose exec backend python -m scripts.sync_inaturalist --limit 100
  docker compose exec backend python -m scripts.sync_inaturalist --ranks Species Genus Family
  docker compose exec backend python -m scripts.sync_inaturalist --refresh --limit 1000
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import text

from app.database import async_session_factory
from app.services.inaturalist_sync import sync_taxon_inaturalist

log = logging.getLogger("sync_inaturalist")

DEFAULT_RANKS = ("Species", "Genus", "Family")


@dataclass
class Stats:
    processed: int = 0
    api_called: int = 0
    found: int = 0
    not_found: int = 0
    vernaculars: int = 0
    failed: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch-sync taxa from iNaturalist")
    parser.add_argument("--limit", type=int, default=None, help="Maximum taxa to process")
    parser.add_argument("--offset", type=int, default=0, help="Offset within selected taxa")
    parser.add_argument(
        "--ranks",
        nargs="+",
        default=list(DEFAULT_RANKS),
        help="Taxon ranks to sync; default: Species Genus Family",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh taxa even when taxa_inaturalist already has a cached row",
    )
    parser.add_argument(
        "--include-unaccepted",
        action="store_true",
        help="Include taxa whose status is not accepted/valid",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.25,
        help="Seconds to sleep after each external API call; default: 0.25",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=20,
        help="Commit after this many processed taxa; default: 20",
    )
    return parser.parse_args()


async def select_taxa(args: argparse.Namespace) -> list[dict]:
    clauses = ["t.scientificname IS NOT NULL", "t.rank = ANY(:ranks)"]
    params: dict[str, object] = {"ranks": args.ranks, "offset": args.offset}
    if not args.refresh:
        clauses.append("i.aphia_id IS NULL")
    if not args.include_unaccepted:
        clauses.append("COALESCE(t.status, '') IN ('accepted', 'valid')")
    limit_sql = ""
    if args.limit is not None:
        limit_sql = "LIMIT :limit"
        params["limit"] = args.limit

    async with async_session_factory() as db:
        rows = await db.execute(
            text(f"""
                SELECT t.aphia_id, t.scientificname, t.rank
                FROM taxa t
                LEFT JOIN taxa_inaturalist i ON i.aphia_id = t.aphia_id
                WHERE {' AND '.join(clauses)}
                ORDER BY t.aphia_id
                OFFSET :offset
                {limit_sql}
            """),
            params,
        )
        return [dict(r._mapping) for r in rows]


async def run(args: argparse.Namespace) -> Stats:
    taxa = await select_taxa(args)
    stats = Stats()
    log.info("selected %d taxa for iNaturalist sync", len(taxa))

    async with async_session_factory() as db:
        for row in taxa:
            aphia_id = int(row["aphia_id"])
            try:
                sync = await sync_taxon_inaturalist(
                    db,
                    aphia_id=aphia_id,
                    scientific_name=row["scientificname"],
                    rank=row["rank"],
                    refresh=args.refresh,
                )
                stats.processed += 1
                if sync.api_called:
                    stats.api_called += 1
                    if args.sleep > 0:
                        await asyncio.sleep(args.sleep)
                if sync.result.found:
                    stats.found += 1
                    stats.vernaculars += len(sync.result.vernaculars)
                else:
                    stats.not_found += 1
            except Exception:
                stats.failed += 1
                log.exception("failed to sync aphia_id=%s", aphia_id)
                await db.rollback()
                continue

            if stats.processed % max(1, args.commit_every) == 0:
                await db.commit()
                log.info(
                    "progress processed=%d api=%d found=%d not_found=%d vernaculars=%d failed=%d",
                    stats.processed,
                    stats.api_called,
                    stats.found,
                    stats.not_found,
                    stats.vernaculars,
                    stats.failed,
                )

        await db.commit()

    return stats


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()
    stats = asyncio.run(run(args))
    log.info(
        "done processed=%d api=%d found=%d not_found=%d vernaculars=%d failed=%d",
        stats.processed,
        stats.api_called,
        stats.found,
        stats.not_found,
        stats.vernaculars,
        stats.failed,
    )


if __name__ == "__main__":
    main()
