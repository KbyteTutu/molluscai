#!/usr/bin/env python3
"""Import a WoRMS-dump SQLite snapshot into the Postgres taxa.* tables.

Reads ``data_import/worms_mollusca.sqlite`` (or any other path passed on the
CLI) produced by ``scripts/worms/worms_dump.py`` and bulk-upserts every table
into Postgres. Idempotent and re-runnable.

Usage (inside the backend container)::

    docker compose exec -T backend \\
        python -m scripts.import_worms_sqlite /app/data_import/worms_mollusca.sqlite

Accepts ``.sqlite`` and ``.sqlite.gz``; the latter is decompressed to a
temporary file before opening.
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import logging
import shutil
import sqlite3
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

import asyncpg

from app.config import settings

log = logging.getLogger("import_worms_sqlite")

BATCH = 5000

EXTRAS_SQL = """
CREATE TABLE IF NOT EXISTS taxa_classification (
    aphia_id            INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    ancestor_aphia_id   INTEGER NOT NULL,
    rank                TEXT,
    scientificname      TEXT NOT NULL,
    depth               INTEGER NOT NULL,
    PRIMARY KEY (aphia_id, ancestor_aphia_id)
);
CREATE INDEX IF NOT EXISTS idx_cls_ancestor ON taxa_classification (ancestor_aphia_id);
CREATE INDEX IF NOT EXISTS idx_cls_depth    ON taxa_classification (aphia_id, depth);

CREATE TABLE IF NOT EXISTS taxa_children (
    parent_aphia_id     INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    child_aphia_id      INTEGER NOT NULL,
    rank                TEXT,
    scientificname      TEXT,
    status              TEXT,
    PRIMARY KEY (parent_aphia_id, child_aphia_id)
);
CREATE INDEX IF NOT EXISTS idx_chld_child  ON taxa_children (child_aphia_id);
CREATE INDEX IF NOT EXISTS idx_chld_status ON taxa_children (parent_aphia_id, status);

CREATE TABLE IF NOT EXISTS taxa_attributes (
    id                      BIGSERIAL PRIMARY KEY,
    aphia_id                INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    measurement_type        TEXT,
    measurement_type_id     INTEGER,
    measurement_value       TEXT,
    category_id             INTEGER,
    aphia_id_inherited      INTEGER,
    quality_status          TEXT,
    source_id               INTEGER,
    reference               TEXT,
    raw                     JSONB
);
CREATE INDEX IF NOT EXISTS idx_attr_aphia ON taxa_attributes (aphia_id);
CREATE INDEX IF NOT EXISTS idx_attr_type  ON taxa_attributes (measurement_type);

CREATE TABLE IF NOT EXISTS taxa_external_ids (
    aphia_id            INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    source              TEXT NOT NULL,
    external_id         TEXT NOT NULL,
    PRIMARY KEY (aphia_id, source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_extid_source ON taxa_external_ids (source, external_id);

CREATE INDEX IF NOT EXISTS idx_taxa_sciname_trgm
    ON taxa USING GIN (scientificname gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_syn_sciname_trgm
    ON taxa_synonyms USING GIN (scientificname gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_vern_trgm
    ON taxa_vernaculars USING GIN (vernacular gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_taxa_sciname_lower
    ON taxa (lower(scientificname));
CREATE INDEX IF NOT EXISTS idx_syn_sciname_lower
    ON taxa_synonyms (lower(scientificname));
CREATE INDEX IF NOT EXISTS idx_vern_lower
    ON taxa_vernaculars (lower(vernacular));
"""


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    return bool(value)


def _json(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    return value


@contextmanager
def open_sqlite(path: Path) -> Iterator[sqlite3.Connection]:
    if path.suffix == ".gz":
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            log.info("decompressing %s -> %s", path, tmp_path)
            with gzip.open(path, "rb") as src, open(tmp_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
            try:
                yield conn
            finally:
                conn.close()
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            yield conn
        finally:
            conn.close()


def iter_batched(cursor: sqlite3.Cursor, size: int = BATCH) -> Iterator[list[tuple]]:
    while True:
        rows = cursor.fetchmany(size)
        if not rows:
            return
        yield rows


async def ensure_schema(pg: asyncpg.Connection) -> None:
    log.info("ensuring extras schema (CREATE TABLE IF NOT EXISTS ...)")
    await pg.execute(EXTRAS_SQL)


async def import_taxa(pg: asyncpg.Connection, sq: sqlite3.Connection) -> int:
    cur = sq.execute("""
        SELECT aphia_id, valid_aphia_id, valid_name, valid_authority,
               scientificname, authority, rank, rank_id, status, unaccept_reason,
               parent_aphia_id, original_aphia_id,
               kingdom, phylum, class_, "order", family, genus,
               is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct,
               citation, lsid, url, api_modified, raw
        FROM taxa
    """)
    total = 0
    for batch in iter_batched(cur):
        records = []
        for r in batch:
            (aphia_id, valid_aphia_id, valid_name, valid_authority,
             scientificname, authority, rank, rank_id, status, unaccept_reason,
             parent_aphia_id, original_aphia_id,
             kingdom, phylum, class_, order_, family, genus,
             is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct,
             citation, lsid, url, api_modified, raw) = r
            species_epithet = None
            if rank == "Species" and scientificname:
                parts = scientificname.split()
                if len(parts) >= 2:
                    species_epithet = parts[1]
            records.append((
                aphia_id, scientificname, authority, rank, rank_id, status,
                unaccept_reason, valid_aphia_id, valid_name, valid_authority,
                parent_aphia_id, original_aphia_id,
                kingdom, phylum, class_, order_, family, genus, species_epithet,
                _bool(is_marine), _bool(is_brackish), _bool(is_freshwater),
                _bool(is_terrestrial), _bool(is_extinct),
                citation, lsid, url, _parse_iso(api_modified),
                _json(raw),
            ))
        await pg.executemany(
            """
            INSERT INTO taxa (
                aphia_id, scientificname, authority, rank, rank_id, status,
                unaccept_reason, valid_aphia_id, valid_name, valid_authority,
                parent_aphia_id, original_name_usage_id,
                kingdom, phylum, class, "order", family, genus, species_epithet,
                is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct,
                citation, lsid, url, api_modified,
                data_source, last_synced_at, raw
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,
                    $13,$14,$15,$16,$17,$18,$19,
                    $20,$21,$22,$23,$24,
                    $25,$26,$27,$28,
                    'worms', now(), $29::jsonb)
            ON CONFLICT (aphia_id) DO UPDATE SET
                scientificname  = EXCLUDED.scientificname,
                authority       = EXCLUDED.authority,
                rank            = EXCLUDED.rank,
                rank_id         = EXCLUDED.rank_id,
                status          = EXCLUDED.status,
                unaccept_reason = EXCLUDED.unaccept_reason,
                valid_aphia_id  = EXCLUDED.valid_aphia_id,
                valid_name      = EXCLUDED.valid_name,
                valid_authority = EXCLUDED.valid_authority,
                parent_aphia_id = EXCLUDED.parent_aphia_id,
                original_name_usage_id = EXCLUDED.original_name_usage_id,
                kingdom         = EXCLUDED.kingdom,
                phylum          = EXCLUDED.phylum,
                class           = EXCLUDED.class,
                "order"         = EXCLUDED."order",
                family          = EXCLUDED.family,
                genus           = EXCLUDED.genus,
                species_epithet = COALESCE(EXCLUDED.species_epithet, taxa.species_epithet),
                is_marine       = EXCLUDED.is_marine,
                is_brackish     = EXCLUDED.is_brackish,
                is_freshwater   = EXCLUDED.is_freshwater,
                is_terrestrial  = EXCLUDED.is_terrestrial,
                is_extinct      = EXCLUDED.is_extinct,
                citation        = EXCLUDED.citation,
                lsid            = EXCLUDED.lsid,
                url             = EXCLUDED.url,
                api_modified    = EXCLUDED.api_modified,
                raw             = EXCLUDED.raw,
                data_source     = CASE
                    WHEN taxa.data_source = 'xlsx'   THEN 'merged'
                    WHEN taxa.data_source = 'merged' THEN 'merged'
                    ELSE 'worms'
                END,
                last_synced_at  = now(),
                updated_at      = now()
            """,
            records,
        )
        total += len(records)
        if total % (BATCH * 10) == 0:
            log.info("  taxa upserted: %d", total)
    return total


async def import_synonyms(pg: asyncpg.Connection, sq: sqlite3.Connection) -> int:
    await pg.execute("DELETE FROM taxa_synonyms")
    cur = sq.execute("""
        SELECT aphia_id, synonym_aphia_id, scientificname, authority, status, raw
        FROM synonyms
    """)
    total = 0
    for batch in iter_batched(cur):
        records = [
            (a, s, n, auth, st, _json(raw))
            for (a, s, n, auth, st, raw) in batch
        ]
        await pg.executemany(
            """
            INSERT INTO taxa_synonyms
                (aphia_id, synonym_aphia_id, scientificname, authority, status, raw)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            ON CONFLICT (aphia_id, synonym_aphia_id) DO NOTHING
            """,
            records,
        )
        total += len(records)
    return total


async def import_vernaculars(pg: asyncpg.Connection, sq: sqlite3.Connection) -> int:
    await pg.execute("DELETE FROM taxa_vernaculars")
    cur = sq.execute("""
        SELECT aphia_id, vernacular, language_code, raw FROM vernaculars
    """)
    total = 0
    for batch in iter_batched(cur):
        records = [(a, v, lc, _json(raw)) for (a, v, lc, raw) in batch]
        await pg.executemany(
            """
            INSERT INTO taxa_vernaculars (aphia_id, vernacular, language_code, raw)
            VALUES ($1, $2, $3, $4::jsonb)
            """,
            records,
        )
        total += len(records)
    return total


async def import_sources(pg: asyncpg.Connection, sq: sqlite3.Connection) -> int:
    await pg.execute("DELETE FROM taxa_sources")
    cur = sq.execute("""
        SELECT aphia_id, source_id, use_, reference, page, url, link, doi, raw
        FROM sources
    """)
    total = 0
    for batch in iter_batched(cur):
        records = [
            (aphia_id, source_id, use_, reference, page, url, link, doi, _json(raw))
            for (aphia_id, source_id, use_, reference, page, url, link, doi, raw) in batch
        ]
        await pg.executemany(
            """
            INSERT INTO taxa_sources
                (aphia_id, source_id, use_type, reference, page, url, link, doi, raw)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
            """,
            records,
        )
        total += len(records)
    return total


async def import_distributions(pg: asyncpg.Connection, sq: sqlite3.Connection) -> int:
    await pg.execute("DELETE FROM taxa_distributions")
    cur = sq.execute("""
        SELECT aphia_id, locality, locality_id, higher_geography,
               higher_geography_id, establishment_means,
               decimal_latitude, decimal_longitude, qualitystatus, raw
        FROM distributions
    """)
    total = 0
    for batch in iter_batched(cur):
        records = [
            (a, loc, loc_id, hg, hg_id, em, lat, lng, qs, _json(raw))
            for (a, loc, loc_id, hg, hg_id, em, lat, lng, qs, raw) in batch
        ]
        await pg.executemany(
            """
            INSERT INTO taxa_distributions
                (aphia_id, locality, locality_id, higher_geography,
                 higher_geography_id, establishment_means,
                 decimal_latitude, decimal_longitude, quality_status, raw)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
            """,
            records,
        )
        total += len(records)
    return total


async def import_classification(pg: asyncpg.Connection, sq: sqlite3.Connection) -> int:
    await pg.execute("DELETE FROM taxa_classification")
    cur = sq.execute("""
        SELECT aphia_id, ancestor_aphia_id, rank, scientificname, depth
        FROM classification
    """)
    total = 0
    for batch in iter_batched(cur):
        await pg.executemany(
            """
            INSERT INTO taxa_classification
                (aphia_id, ancestor_aphia_id, rank, scientificname, depth)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (aphia_id, ancestor_aphia_id) DO NOTHING
            """,
            list(batch),
        )
        total += len(batch)
        if total % (BATCH * 20) == 0:
            log.info("  classification upserted: %d", total)
    return total


async def import_children(pg: asyncpg.Connection, sq: sqlite3.Connection) -> int:
    await pg.execute("DELETE FROM taxa_children")
    cur = sq.execute("""
        SELECT parent_aphia_id, child_aphia_id, rank, scientificname, status
        FROM children
    """)
    total = 0
    for batch in iter_batched(cur):
        await pg.executemany(
            """
            INSERT INTO taxa_children
                (parent_aphia_id, child_aphia_id, rank, scientificname, status)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (parent_aphia_id, child_aphia_id) DO NOTHING
            """,
            list(batch),
        )
        total += len(batch)
    return total


async def import_attributes(pg: asyncpg.Connection, sq: sqlite3.Connection) -> int:
    await pg.execute("DELETE FROM taxa_attributes")
    cur = sq.execute("""
        SELECT aphia_id, measurement_type, measurement_type_id, measurement_value,
               category_id, aphia_id_inherited, qualitystatus, source_id,
               reference, raw
        FROM attributes
    """)
    total = 0
    for batch in iter_batched(cur):
        records = [
            (a, mt, mtid, mv, cid, aii, qs, sid, ref, _json(raw))
            for (a, mt, mtid, mv, cid, aii, qs, sid, ref, raw) in batch
        ]
        await pg.executemany(
            """
            INSERT INTO taxa_attributes
                (aphia_id, measurement_type, measurement_type_id, measurement_value,
                 category_id, aphia_id_inherited, quality_status, source_id,
                 reference, raw)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
            """,
            records,
        )
        total += len(records)
    return total


async def import_external_ids(pg: asyncpg.Connection, sq: sqlite3.Connection) -> int:
    await pg.execute("DELETE FROM taxa_external_ids")
    cur = sq.execute("""
        SELECT aphia_id, source, external_id FROM external_ids
    """)
    total = 0
    for batch in iter_batched(cur):
        await pg.executemany(
            """
            INSERT INTO taxa_external_ids (aphia_id, source, external_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (aphia_id, source, external_id) DO NOTHING
            """,
            list(batch),
        )
        total += len(batch)
    return total


async def run(sqlite_path: Path) -> None:
    if not sqlite_path.exists():
        log.error("input not found: %s", sqlite_path)
        sys.exit(2)

    log.info("source: %s (%.1f MB)", sqlite_path, sqlite_path.stat().st_size / 1024 / 1024)
    log.info("target: %s", settings.DATABASE_URL_SYNC)

    started = time.monotonic()
    with open_sqlite(sqlite_path) as sq:
        meta = dict(sq.execute("SELECT key, value FROM meta").fetchall())
        log.info("dump meta: root=%s started=%s finished=%s",
                 meta.get("root"), meta.get("started_at"), meta.get("finished_at"))

        pg = await asyncpg.connect(settings.DATABASE_URL_SYNC)
        try:
            await ensure_schema(pg)

            log.info("importing taxa ...")
            n_taxa = await import_taxa(pg, sq)

            log.info("importing synonyms ...")
            n_syn = await import_synonyms(pg, sq)

            log.info("importing vernaculars ...")
            n_vern = await import_vernaculars(pg, sq)

            log.info("importing sources ...")
            n_src = await import_sources(pg, sq)

            log.info("importing distributions ...")
            n_dist = await import_distributions(pg, sq)

            log.info("importing classification (this is the big one) ...")
            n_cls = await import_classification(pg, sq)

            log.info("importing children ...")
            n_chld = await import_children(pg, sq)

            log.info("importing attributes ...")
            n_attr = await import_attributes(pg, sq)

            log.info("importing external_ids ...")
            n_ext = await import_external_ids(pg, sq)

            log.info("running ANALYZE ...")
            for tbl in ("taxa", "taxa_synonyms", "taxa_vernaculars",
                        "taxa_sources", "taxa_distributions",
                        "taxa_classification", "taxa_children",
                        "taxa_attributes", "taxa_external_ids"):
                await pg.execute(f"ANALYZE {tbl}")
        finally:
            await pg.close()

    elapsed = time.monotonic() - started
    log.info("=" * 60)
    log.info("DONE in %.1fs", elapsed)
    log.info("  taxa:           %s", f"{n_taxa:,}")
    log.info("  synonyms:       %s", f"{n_syn:,}")
    log.info("  vernaculars:    %s", f"{n_vern:,}")
    log.info("  sources:        %s", f"{n_src:,}")
    log.info("  distributions:  %s", f"{n_dist:,}")
    log.info("  classification: %s", f"{n_cls:,}")
    log.info("  children:       %s", f"{n_chld:,}")
    log.info("  attributes:     %s", f"{n_attr:,}")
    log.info("  external_ids:   %s", f"{n_ext:,}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("sqlite_path", type=Path,
                        help="Path to worms_mollusca.sqlite or .sqlite.gz")
    parser.add_argument("--quiet", action="store_true",
                        help="Reduce log noise (warnings only)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
    )

    try:
        asyncio.run(run(args.sqlite_path))
    except KeyboardInterrupt:
        log.warning("interrupted")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
