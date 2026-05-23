"""
Import Chinese vernacular names from ganvana.xlsx into taxa_vernaculars.

Matching: for each taxon, take first 1-2 words of scientificname,
look up in ganvana dict, insert Chinese name as zh vernacular.

Usage:
  docker compose exec backend python -m scripts.import_ganvana_zh
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import asyncpg
import openpyxl

from app.config import settings

log = logging.getLogger("import_ganvana_zh")

XLSX_PATH = Path(__file__).resolve().parent.parent / "data_import" / "ganvana.xlsx"
BATCH_SIZE = 5000


def parse_xlsx() -> dict[str, str]:
    wb = openpyxl.load_workbook(str(XLSX_PATH), read_only=True)
    ws = wb["v1"]
    mapping: dict[str, str] = {}
    for row in ws.iter_rows(min_row=2, max_col=4, values_only=True):
        chinese, _, latin = row[1], row[2], row[3]
        if not chinese or not latin:
            continue
        chinese = str(chinese).strip()
        latin = str(latin).strip().lower()
        if not chinese or not latin:
            continue
        key = " ".join(latin.split()[:2])
        if key not in mapping:
            mapping[key] = chinese
    wb.close()
    log.info("parsed %d unique keys", len(mapping))
    return mapping


def key_of(scientificname: str) -> str:
    words = (scientificname or "").strip().lower().split()
    return " ".join(words[:2])


async def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    if not XLSX_PATH.exists():
        log.error("xlsx not found: %s", XLSX_PATH)
        return 1
    mapping = parse_xlsx()
    if not mapping:
        return 1
    pool = await asyncpg.create_pool(settings.DATABASE_URL_SYNC, min_size=2, max_size=4)
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM taxa_vernaculars WHERE language_code = 'CHN'")
            total = await conn.fetchval("SELECT COUNT(*) FROM taxa")
            log.info("cleared old CHN vernaculars; %d taxa total", total)
            offset = 0
            total_inserted = 0
            total_matched = 0
            while True:
                rows = await conn.fetch(
                    "SELECT aphia_id, scientificname FROM taxa ORDER BY aphia_id LIMIT $1 OFFSET $2",
                    BATCH_SIZE, offset,
                )
                if not rows:
                    break
                batch_entries = []
                for r in rows:
                    k = key_of(r["scientificname"])
                    zh = mapping.get(k)
                    if zh:
                        batch_entries.append((r["aphia_id"], zh))
                        total_matched += 1
                if batch_entries:
                    await conn.executemany(
                        "INSERT INTO taxa_vernaculars (aphia_id, vernacular, language_code) VALUES ($1, $2, 'CHN') ON CONFLICT DO NOTHING",
                        batch_entries,
                    )
                    total_inserted += len(batch_entries)
                offset += BATCH_SIZE
                if offset % 50000 == 0:
                    log.info("progress: %d/%d  matched=%d inserted=%d", offset, total, total_matched, total_inserted)
            count = await conn.fetchval("SELECT COUNT(*) FROM taxa_vernaculars WHERE language_code = 'CHN'")
            log.info("done. total CHN vernaculars: %d  (matched %d taxa of %d)", count, total_matched, total)
    finally:
        await pool.close()
    return 0


def main() -> int:
    return asyncio.run(run())

if __name__ == "__main__":
    sys.exit(main())
