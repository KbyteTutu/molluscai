"""
Import Chinese vernacular names from ganvana.xlsx into taxa_vernaculars.

Matching: strict full-name match.  Strip author/year/subgenus from ganvana
latin names, then compare cleaned name against cleaned taxa.scientificname.

Only matches when genus + species + form ALL agree — no greedy truncation.
If no exact match, leave blank rather than fill incorrectly.

Usage:
  docker compose exec backend python -m scripts.import_ganvana_zh
"""
from __future__ import annotations

import asyncio
import logging
import re
import sys
from pathlib import Path

import asyncpg
import openpyxl
import zhconv

from app.config import settings

log = logging.getLogger("import_ganvana_zh")

XLSX_PATH = Path(__file__).resolve().parent.parent / "data_import" / "ganvana.xlsx"
BATCH_SIZE = 5000

# ── cleaning patterns ──────────────────────────────────────────────

# (Author, Year) or (Author Year) — parenthesized with a 4-digit year
_AUTHOR_PAREN_RE = re.compile(
    r'[\(\[（]\s*[^)\]]*?\d{4}[^)\]]*?\s*[\)\]）]'
)

# Trailing "Author, Year" or "Author Author, Year" (no parens)
_AUTHOR_TRAILING_RE = re.compile(
    r'\s+(?:[A-Z][a-zéèêëàâîïôûçüöäñ]+\.?\s+)?[A-Z][a-zéèêëàâîïôûçüöäñ]+[，,]\s*1[789]\d{2}\s*$'
)

# Bare author surname(s) at end (no parens, no comma, no year).
# Genus=capitalized, species=lowercase → any capitalized word
# after the binomial is an author name (infraspecific epithets are lowercase).
# "Conus figulinus Linnaeus" → strip " Linnaeus"
# "Conus otohimeae Kuroda et Ito" → strip " Kuroda et Ito"
_BARE_AUTHOR_END_RE = re.compile(
    r'(?:\s+[A-Z][a-zéèêëàâîïôûçüöäñA-Z\u3000-\u303f．\.\-]*)+(?:\s+et)?(?:\s+[A-Z][a-zéèêëàâîïôûçüöäñA-Z．\.\-]*)*\s*$'
)

# Subgenus in parentheses: (Capitalizedword) or (lowercase)
_SUBGENUS_RE = re.compile(
    r'\s*[\(\[（][A-Za-z][a-z]+[\)\]）]'
)

# (fossil) / (化石) / (sensu lato) etc.
_FOSSIL_RE = re.compile(
    r'\s*[\(\[（]\s*(?:fossil|化石|sensu\s+lato|sensu\s+stricto)\s*[\)\]）]',
    re.IGNORECASE,
)

# Multiple whitespace
_SPACE_RE = re.compile(r'\s+')


def clean_name(raw: str) -> str:
    """Clean a scientific name for strict matching.

    Strips: author/year, subgenus, fossil markers.
    Normalizes: Chinese→ASCII punctuation, whitespace, lowercase.

    Returns empty string if nothing remains after cleaning.
    """
    if not raw or not raw.strip():
        return ""
    c = raw.strip()
    c = c.replace('\u3001', '')   # 、 (enumeration comma)
    c = c.replace('\uff0c', ',')   # ，
    c = c.replace('\uff08', '(')   # （
    c = c.replace('\uff09', ')')   # ）
    c = c.replace('\u00a0', ' ')   # non-breaking space
    c = _AUTHOR_PAREN_RE.sub('', c)
    c = _AUTHOR_TRAILING_RE.sub('', c)
    c = _BARE_AUTHOR_END_RE.sub('', c)
    c = _SUBGENUS_RE.sub('', c)
    c = _FOSSIL_RE.sub('', c)
    c = c.strip('.,;: ')
    c = _SPACE_RE.sub(' ', c).strip()
    return c.lower()


def parse_xlsx() -> dict[str, str]:
    """Build {cleaned_latin_name: chinese_name} mapping from ganvana.xlsx.

    Each entry's latin name is cleaned via clean_name().
    First-come-first-served for duplicate cleaned names.
    """
    wb = openpyxl.load_workbook(str(XLSX_PATH), read_only=True)
    ws = wb["v1"]
    mapping: dict[str, str] = {}
    skipped = 0
    for row in ws.iter_rows(min_row=2, max_col=4, values_only=True):
        chinese, _, latin = row[1], row[2], row[3]
        if not chinese or not latin:
            continue
        chinese = zhconv.convert(str(chinese).strip(), 'zh-cn')
        if not chinese:
            continue
        key = clean_name(str(latin))
        if not key:
            skipped += 1
            continue
        if key not in mapping:
            mapping[key] = chinese
    wb.close()
    log.info("parsed %d unique keys (%d skipped: unparseable)", len(mapping), skipped)
    return mapping


def key_of(scientificname: str) -> str:
    """Compute lookup key from taxa.scientificname.

    Uses the same clean_name() logic: strips subgenus parentheses
    (no author/year in DB, but subgenus may be present).
    """
    return clean_name(scientificname or "")


async def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    if not XLSX_PATH.exists():
        log.error("xlsx not found: %s", XLSX_PATH)
        return 1
    mapping = parse_xlsx()
    if not mapping:
        log.error("no entries parsed from xlsx")
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
