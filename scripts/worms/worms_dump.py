#!/usr/bin/env python3
"""
worms_dump.py — Standalone WoRMS / MarineSpecies REST mirror.

Walks an AphiaID subtree (default Mollusca = 51), fetches AphiaRecord +
synonyms + vernaculars + sources + distributions for every taxon, writes
to a local SQLite file. Designed to run on a fast overseas node; ship
the gzipped output back home for import into Postgres.

Zero project dependencies. Single file. Resumable. Concurrent. Polite.

Usage:
    pip install -r requirements.txt
    python3 worms_dump.py --root 51 --out worms_mollusca.sqlite

Data source attribution (REQUIRED on any UI displaying this data):
    WoRMS Editorial Board. World Register of Marine Species.
    Available from https://www.marinespecies.org at VLIZ.
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import logging
import shutil
import signal
import sqlite3
import sys
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import httpx
from tqdm import tqdm

API_BASE = "https://www.marinespecies.org/rest"
USER_AGENT = "MalacoAgent-Dump/0.1 (mollusca-knowledge-platform; one-time scientific mirror)"
RANK_ORDER = {
    "Kingdom": 0, "Subkingdom": 1, "Infrakingdom": 2,
    "Phylum": 10, "Subphylum": 11, "Superclass": 19,
    "Class": 20, "Subclass": 21, "Infraclass": 22,
    "Superorder": 29, "Order": 30, "Suborder": 31, "Infraorder": 32,
    "Superfamily": 39, "Family": 40, "Subfamily": 41, "Tribe": 42, "Subtribe": 43,
    "Genus": 50, "Subgenus": 51,
    "Species": 60, "Subspecies": 61, "Variety": 62, "Form": 63,
}

log = logging.getLogger("worms_dump")


SCHEMA = """
CREATE TABLE IF NOT EXISTS taxa (
    aphia_id INTEGER PRIMARY KEY,
    valid_aphia_id INTEGER,
    valid_name TEXT,
    valid_authority TEXT,
    scientificname TEXT NOT NULL,
    authority TEXT,
    rank TEXT,
    rank_id INTEGER,
    status TEXT,
    unaccept_reason TEXT,
    parent_aphia_id INTEGER,
    original_aphia_id INTEGER,
    kingdom TEXT, phylum TEXT, class_ TEXT, "order" TEXT, family TEXT, genus TEXT,
    is_marine INTEGER, is_brackish INTEGER, is_freshwater INTEGER,
    is_terrestrial INTEGER, is_extinct INTEGER,
    match_type TEXT,
    citation TEXT,
    lsid TEXT,
    url TEXT,
    api_modified TEXT,
    fetched_at TEXT NOT NULL,
    raw TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_taxa_parent ON taxa(parent_aphia_id);
CREATE INDEX IF NOT EXISTS idx_taxa_valid ON taxa(valid_aphia_id);
CREATE INDEX IF NOT EXISTS idx_taxa_original ON taxa(original_aphia_id);
CREATE INDEX IF NOT EXISTS idx_taxa_name ON taxa(scientificname);

CREATE TABLE IF NOT EXISTS synonyms (
    aphia_id INTEGER NOT NULL,
    synonym_aphia_id INTEGER NOT NULL,
    scientificname TEXT NOT NULL,
    authority TEXT,
    status TEXT,
    raw TEXT NOT NULL,
    PRIMARY KEY (aphia_id, synonym_aphia_id)
);

CREATE TABLE IF NOT EXISTS vernaculars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aphia_id INTEGER NOT NULL,
    vernacular TEXT NOT NULL,
    language_code TEXT,
    raw TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vern_aphia ON vernaculars(aphia_id);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aphia_id INTEGER NOT NULL,
    source_id INTEGER,
    use_ TEXT,
    reference TEXT,
    page TEXT,
    url TEXT,
    link TEXT,
    fulltext TEXT,
    doi TEXT,
    raw TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_src_aphia ON sources(aphia_id);

CREATE TABLE IF NOT EXISTS distributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aphia_id INTEGER NOT NULL,
    locality TEXT,
    locality_id TEXT,
    higher_geography TEXT,
    higher_geography_id TEXT,
    establishment_means TEXT,
    decimal_latitude REAL,
    decimal_longitude REAL,
    qualitystatus TEXT,
    raw TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dist_aphia ON distributions(aphia_id);

CREATE TABLE IF NOT EXISTS classification (
    aphia_id INTEGER NOT NULL,
    ancestor_aphia_id INTEGER NOT NULL,
    rank TEXT,
    scientificname TEXT NOT NULL,
    depth INTEGER NOT NULL,
    PRIMARY KEY (aphia_id, ancestor_aphia_id)
);
CREATE INDEX IF NOT EXISTS idx_cls_ancestor ON classification(ancestor_aphia_id);

CREATE TABLE IF NOT EXISTS children (
    parent_aphia_id INTEGER NOT NULL,
    child_aphia_id INTEGER NOT NULL,
    rank TEXT,
    scientificname TEXT,
    status TEXT,
    PRIMARY KEY (parent_aphia_id, child_aphia_id)
);
CREATE INDEX IF NOT EXISTS idx_chld_child ON children(child_aphia_id);

CREATE TABLE IF NOT EXISTS attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aphia_id INTEGER NOT NULL,
    measurement_type TEXT,
    measurement_type_id INTEGER,
    measurement_value TEXT,
    category_id INTEGER,
    aphia_id_inherited INTEGER,
    qualitystatus TEXT,
    source_id INTEGER,
    reference TEXT,
    raw TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attr_aphia ON attributes(aphia_id);

CREATE TABLE IF NOT EXISTS external_ids (
    aphia_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    PRIMARY KEY (aphia_id, source, external_id)
);

CREATE TABLE IF NOT EXISTS frontier (
    aphia_id INTEGER PRIMARY KEY,
    depth INTEGER NOT NULL,
    state TEXT NOT NULL,
    enqueued_at TEXT NOT NULL,
    finished_at TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_frontier_state ON frontier(state);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@dataclass
class Config:
    root: int
    out: Path
    concurrency: int
    min_interval: float
    max_depth: int
    timeout: float
    max_retries: int


def open_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.executescript(SCHEMA)
    return conn


def meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", (key, value))


def meta_get(conn: sqlite3.Connection, key: str, default: Optional[str] = None) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def enqueue(conn: sqlite3.Connection, aphia_id: int, depth: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO frontier(aphia_id, depth, state, enqueued_at) "
        "VALUES (?, ?, 'pending', datetime('now'))",
        (aphia_id, depth),
    )


def pick_pending(conn: sqlite3.Connection, n: int) -> list[tuple[int, int]]:
    rows = conn.execute(
        "SELECT aphia_id, depth FROM frontier WHERE state = 'pending' LIMIT ?",
        (n,),
    ).fetchall()
    return [(int(r[0]), int(r[1])) for r in rows]


def mark_running(conn: sqlite3.Connection, aphia_id: int) -> None:
    conn.execute("UPDATE frontier SET state='running' WHERE aphia_id = ?", (aphia_id,))


def mark_done(conn: sqlite3.Connection, aphia_id: int) -> None:
    conn.execute(
        "UPDATE frontier SET state='done', finished_at=datetime('now'), error=NULL WHERE aphia_id = ?",
        (aphia_id,),
    )


def mark_failed(conn: sqlite3.Connection, aphia_id: int, err: str) -> None:
    conn.execute(
        "UPDATE frontier SET state='failed', finished_at=datetime('now'), error=? WHERE aphia_id = ?",
        (err[:500], aphia_id),
    )


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    out = {}
    for state in ("pending", "running", "done", "failed"):
        out[state] = conn.execute(
            "SELECT COUNT(*) FROM frontier WHERE state = ?", (state,)
        ).fetchone()[0]
    out["taxa"] = conn.execute("SELECT COUNT(*) FROM taxa").fetchone()[0]
    return out


def reset_running(conn: sqlite3.Connection) -> int:
    """On restart, anything 'running' was interrupted — return it to pending."""
    cur = conn.execute("UPDATE frontier SET state='pending' WHERE state='running'")
    return cur.rowcount


class RateLimiter:
    def __init__(self, min_interval: float):
        self._min = min_interval
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if now < self._next:
                await asyncio.sleep(self._next - now)
            self._next = max(now, self._next) + self._min


class WormsClient:
    def __init__(self, cfg: Config, limiter: RateLimiter):
        self.cfg = cfg
        self.limiter = limiter
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            timeout=cfg.timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            http2=False,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=cfg.concurrency * 2, max_keepalive_connections=cfg.concurrency),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, *, params: Optional[dict] = None) -> Optional[Any]:
        """GET path. Returns parsed JSON, or None for 204 / 404. Raises on persistent failure."""
        attempt = 0
        while True:
            await self.limiter.wait()
            try:
                r = await self._client.get(path, params=params or {})
            except (httpx.TransportError, httpx.TimeoutException) as e:
                attempt += 1
                if attempt > self.cfg.max_retries:
                    raise RuntimeError(f"network: {e}") from e
                await asyncio.sleep(min(2 ** attempt, 30))
                continue

            if r.status_code in (204, 404):
                return None
            if r.status_code == 200:
                if not r.content:
                    return None
                try:
                    return r.json()
                except json.JSONDecodeError:
                    return None
            if r.status_code in (429, 500, 502, 503, 504):
                attempt += 1
                if attempt > self.cfg.max_retries:
                    raise RuntimeError(f"http {r.status_code} after {self.cfg.max_retries} retries: {path}")
                retry_after = r.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 60)
                await asyncio.sleep(delay)
                continue
            raise RuntimeError(f"http {r.status_code}: {path}")

    async def record(self, aphia_id: int) -> Optional[dict]:
        return await self._get(f"/AphiaRecordByAphiaID/{aphia_id}")

    async def children(self, aphia_id: int) -> list[dict]:
        out: list[dict] = []
        offset = 1
        while True:
            page = await self._get(
                f"/AphiaChildrenByAphiaID/{aphia_id}",
                params={"marine_only": "false", "offset": offset},
            )
            if not page:
                break
            if not isinstance(page, list):
                break
            out.extend(page)
            if len(page) < 50:
                break
            offset += 50
        return out

    async def synonyms(self, aphia_id: int) -> list[dict]:
        data = await self._get(f"/AphiaSynonymsByAphiaID/{aphia_id}")
        return data if isinstance(data, list) else []

    async def vernaculars(self, aphia_id: int) -> list[dict]:
        data = await self._get(f"/AphiaVernacularsByAphiaID/{aphia_id}")
        return data if isinstance(data, list) else []

    async def sources(self, aphia_id: int) -> list[dict]:
        data = await self._get(f"/AphiaSourcesByAphiaID/{aphia_id}")
        return data if isinstance(data, list) else []

    async def distributions(self, aphia_id: int) -> list[dict]:
        data = await self._get(f"/AphiaDistributionsByAphiaID/{aphia_id}")
        return data if isinstance(data, list) else []

    async def classification(self, aphia_id: int) -> Optional[dict]:
        return await self._get(f"/AphiaClassificationByAphiaID/{aphia_id}")

    async def attributes(self, aphia_id: int) -> list[dict]:
        data = await self._get(f"/AphiaAttributesByAphiaID/{aphia_id}")
        return data if isinstance(data, list) else []

    async def external_id(self, aphia_id: int, src: str) -> list[str]:
        try:
            data = await self._get(f"/AphiaExternalIDByAphiaID/{aphia_id}", params={"type": src})
        except RuntimeError as e:
            if "http 400" in str(e):
                return []
            raise
        return [str(x) for x in data] if isinstance(data, list) else []


def insert_taxon(conn: sqlite3.Connection, rec: dict, parent_aphia_id: Optional[int]) -> None:
    rank = rec.get("rank")
    conn.execute(
        """INSERT OR REPLACE INTO taxa
            (aphia_id, valid_aphia_id, valid_name, valid_authority,
             scientificname, authority, rank, rank_id, status, unaccept_reason,
             parent_aphia_id, original_aphia_id,
             kingdom, phylum, class_, "order", family, genus,
             is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct,
             match_type, citation, lsid, url, api_modified, fetched_at, raw)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)""",
        (
            rec.get("AphiaID"),
            rec.get("valid_AphiaID"),
            rec.get("valid_name"),
            rec.get("valid_authority"),
            rec.get("scientificname"),
            rec.get("authority"),
            rank,
            rec.get("taxonRankID") or RANK_ORDER.get(rank or ""),
            rec.get("status"),
            rec.get("unacceptreason"),
            parent_aphia_id if parent_aphia_id is not None else rec.get("parentNameUsageID"),
            rec.get("originalNameUsageID"),
            rec.get("kingdom"), rec.get("phylum"), rec.get("class"),
            rec.get("order"), rec.get("family"), rec.get("genus"),
            rec.get("isMarine"), rec.get("isBrackish"), rec.get("isFreshwater"),
            rec.get("isTerrestrial"), rec.get("isExtinct"),
            rec.get("match_type"),
            rec.get("citation"),
            rec.get("lsid"),
            rec.get("url"),
            rec.get("modified"),
            json.dumps(rec, ensure_ascii=False, sort_keys=True),
        ),
    )


def insert_synonyms(conn: sqlite3.Connection, aphia_id: int, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute("DELETE FROM synonyms WHERE aphia_id = ?", (aphia_id,))
    conn.executemany(
        "INSERT OR REPLACE INTO synonyms(aphia_id, synonym_aphia_id, scientificname, authority, status, raw) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (aphia_id, r.get("AphiaID"), r.get("scientificname"), r.get("authority"),
             r.get("status"), json.dumps(r, ensure_ascii=False, sort_keys=True))
            for r in rows if r.get("AphiaID") is not None
        ],
    )


def insert_vernaculars(conn: sqlite3.Connection, aphia_id: int, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute("DELETE FROM vernaculars WHERE aphia_id = ?", (aphia_id,))
    conn.executemany(
        "INSERT INTO vernaculars(aphia_id, vernacular, language_code, raw) VALUES (?, ?, ?, ?)",
        [
            (aphia_id, r.get("vernacular"), r.get("language_code") or r.get("languagecode"),
             json.dumps(r, ensure_ascii=False, sort_keys=True))
            for r in rows
        ],
    )


def insert_sources(conn: sqlite3.Connection, aphia_id: int, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute("DELETE FROM sources WHERE aphia_id = ?", (aphia_id,))
    conn.executemany(
        "INSERT INTO sources(aphia_id, source_id, use_, reference, page, url, link, fulltext, doi, raw) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (aphia_id, r.get("source_id"), r.get("use"), r.get("reference"),
             r.get("page"), r.get("url"), r.get("link"), r.get("fulltext"), r.get("doi"),
             json.dumps(r, ensure_ascii=False, sort_keys=True))
            for r in rows
        ],
    )


def insert_distributions(conn: sqlite3.Connection, aphia_id: int, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute("DELETE FROM distributions WHERE aphia_id = ?", (aphia_id,))
    conn.executemany(
        """INSERT INTO distributions(aphia_id, locality, locality_id, higher_geography,
            higher_geography_id, establishment_means, decimal_latitude, decimal_longitude,
            qualitystatus, raw) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (aphia_id, r.get("locality"), r.get("locality_id") or r.get("localityID"),
             r.get("higherGeography"), r.get("higherGeographyID"),
             r.get("establishmentMeans"),
             r.get("decimalLatitude"), r.get("decimalLongitude"),
             r.get("qualityStatus"),
             json.dumps(r, ensure_ascii=False, sort_keys=True))
            for r in rows
        ],
    )


def insert_classification(conn: sqlite3.Connection, aphia_id: int, root: Optional[dict]) -> None:
    if not root:
        return
    conn.execute("DELETE FROM classification WHERE aphia_id = ?", (aphia_id,))
    rows: list[tuple] = []
    node = root
    depth = 0
    while node:
        anc = node.get("AphiaID")
        if anc is not None:
            rows.append((aphia_id, anc, node.get("rank"), node.get("scientificname") or "", depth))
        node = node.get("child")
        depth += 1
    if rows:
        conn.executemany(
            "INSERT OR REPLACE INTO classification(aphia_id, ancestor_aphia_id, rank, scientificname, depth) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )


def insert_children(conn: sqlite3.Connection, parent_aphia_id: int, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute("DELETE FROM children WHERE parent_aphia_id = ?", (parent_aphia_id,))
    conn.executemany(
        "INSERT OR REPLACE INTO children(parent_aphia_id, child_aphia_id, rank, scientificname, status) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (parent_aphia_id, r.get("AphiaID"), r.get("rank"),
             r.get("scientificname"), r.get("status"))
            for r in rows if r.get("AphiaID") is not None
        ],
    )


def insert_attributes(conn: sqlite3.Connection, aphia_id: int, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute("DELETE FROM attributes WHERE aphia_id = ?", (aphia_id,))
    flat: list[tuple] = []

    def _walk(items: list[dict]) -> None:
        for it in items:
            flat.append((
                aphia_id,
                it.get("measurementType"),
                it.get("measurementTypeID"),
                it.get("measurementValue"),
                it.get("CategoryID"),
                it.get("AphiaID_Inherited"),
                it.get("qualitystatus"),
                it.get("source_id"),
                it.get("reference"),
                json.dumps(it, ensure_ascii=False, sort_keys=True),
            ))
            kids = it.get("children")
            if isinstance(kids, list):
                _walk(kids)

    _walk(rows)
    if flat:
        conn.executemany(
            """INSERT INTO attributes
                 (aphia_id, measurement_type, measurement_type_id, measurement_value,
                  category_id, aphia_id_inherited, qualitystatus, source_id, reference, raw)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            flat,
        )


def insert_external_ids(conn: sqlite3.Connection, aphia_id: int, by_src: dict[str, list[str]]) -> None:
    conn.execute("DELETE FROM external_ids WHERE aphia_id = ?", (aphia_id,))
    rows = [
        (aphia_id, src, ext_id)
        for src, ids in by_src.items() if ids
        for ext_id in ids
    ]
    if rows:
        conn.executemany(
            "INSERT OR REPLACE INTO external_ids(aphia_id, source, external_id) VALUES (?, ?, ?)",
            rows,
        )


EXTERNAL_ID_SOURCES = ("ncbi", "bold", "lsid", "tsn", "iucnredlist", "fishbase",
                       "algaebase", "dyntaxa", "opac", "plazi")


@dataclass
class WorkerResult:
    aphia_id: int
    rec: Optional[dict]
    children: list[dict]
    synonyms: list[dict]
    vernaculars: list[dict]
    sources: list[dict]
    distributions: list[dict]
    classification: Optional[dict]
    attributes: list[dict]
    external_ids: dict[str, list[str]]
    error: Optional[str] = None


async def process_one(client: WormsClient, aphia_id: int) -> WorkerResult:
    try:
        rec = await client.record(aphia_id)
        if rec is None:
            return WorkerResult(aphia_id, None, [], [], [], [], [], None, [], {},
                                error="record_not_found")
        (children, syns, verns, srcs, dists,
         classification, attrs, *ext_lists) = await asyncio.gather(
            client.children(aphia_id),
            client.synonyms(aphia_id),
            client.vernaculars(aphia_id),
            client.sources(aphia_id),
            client.distributions(aphia_id),
            client.classification(aphia_id),
            client.attributes(aphia_id),
            *(client.external_id(aphia_id, src) for src in EXTERNAL_ID_SOURCES),
        )
        ext_ids = dict(zip(EXTERNAL_ID_SOURCES, ext_lists, strict=True))
        return WorkerResult(aphia_id, rec, children, syns, verns, srcs, dists,
                            classification, attrs, ext_ids)
    except Exception as e:
        return WorkerResult(aphia_id, None, [], [], [], [], [], None, [], {},
                            error=str(e))


async def crawl(cfg: Config, conn: sqlite3.Connection) -> None:
    meta_set(conn, "root", str(cfg.root))
    meta_set(conn, "started_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    meta_set(conn, "max_depth", str(cfg.max_depth))

    resumed = reset_running(conn)
    if resumed:
        log.info("resumed: returned %d 'running' items to 'pending'", resumed)
    enqueue(conn, cfg.root, 0)

    limiter = RateLimiter(cfg.min_interval)
    client = WormsClient(cfg, limiter)

    stop_requested = asyncio.Event()

    def _handle_signal(*_: Any) -> None:
        if not stop_requested.is_set():
            log.warning("\nshutdown requested — finishing in-flight tasks then exiting cleanly")
            stop_requested.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_running_loop().add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            signal.signal(sig, _handle_signal)

    initial = counts(conn)
    pbar = tqdm(
        initial=initial["done"],
        total=initial["done"] + initial["pending"] + initial["running"],
        unit="taxa",
        dynamic_ncols=True,
        smoothing=0.05,
    )

    try:
        sem = asyncio.Semaphore(cfg.concurrency)

        async def runner(aphia_id: int, depth: int) -> WorkerResult:
            async with sem:
                return await process_one(client, aphia_id)

        in_flight: dict[asyncio.Task, tuple[int, int]] = {}
        while True:
            if stop_requested.is_set():
                break

            while len(in_flight) < cfg.concurrency:
                batch = pick_pending(conn, cfg.concurrency * 2)
                batch = [(a, d) for a, d in batch if a not in {v[0] for v in in_flight.values()}]
                if not batch:
                    break
                for aphia_id, depth in batch:
                    mark_running(conn, aphia_id)
                    task = asyncio.create_task(runner(aphia_id, depth))
                    in_flight[task] = (aphia_id, depth)
                    if len(in_flight) >= cfg.concurrency:
                        break

            if not in_flight:
                break

            done, _ = await asyncio.wait(in_flight.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                aphia_id, depth = in_flight.pop(task)
                res: WorkerResult = task.result()
                if res.error and res.rec is None:
                    if res.error == "record_not_found":
                        mark_failed(conn, aphia_id, "record_not_found")
                    else:
                        mark_failed(conn, aphia_id, res.error)
                        log.warning("aphia=%s failed: %s", aphia_id, res.error)
                    pbar.update(1)
                    continue

                rec = res.rec
                insert_taxon(conn, rec, parent_aphia_id=rec.get("parentNameUsageID"))
                insert_synonyms(conn, aphia_id, res.synonyms)
                insert_vernaculars(conn, aphia_id, res.vernaculars)
                insert_sources(conn, aphia_id, res.sources)
                insert_distributions(conn, aphia_id, res.distributions)
                insert_classification(conn, aphia_id, res.classification)
                insert_children(conn, aphia_id, res.children)
                insert_attributes(conn, aphia_id, res.attributes)
                insert_external_ids(conn, aphia_id, res.external_ids)

                if depth < cfg.max_depth:
                    for child in res.children:
                        cid = child.get("AphiaID")
                        if isinstance(cid, int):
                            enqueue(conn, cid, depth + 1)

                mark_done(conn, aphia_id)
                pbar.update(1)
                c = counts(conn)
                pbar.total = c["done"] + c["pending"] + c["running"]
                pbar.set_postfix(pending=c["pending"], failed=c["failed"], refresh=False)

    finally:
        pbar.close()
        await client.close()
        meta_set(conn, "finished_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        c = counts(conn)
        log.info("final: taxa=%d done=%d pending=%d failed=%d",
                 c["taxa"], c["done"], c["pending"], c["failed"])


def gzip_file(src: Path, dst: Optional[Path] = None) -> Path:
    dst = dst or src.with_suffix(src.suffix + ".gz")
    with src.open("rb") as fin, gzip.open(dst, "wb", compresslevel=6) as fout:
        shutil.copyfileobj(fin, fout)
    return dst


def parse_args() -> Config:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", type=int, default=51, help="Root AphiaID (default: 51 = Mollusca)")
    p.add_argument("--out", type=Path, default=Path("worms_dump.sqlite"), help="Output SQLite file")
    p.add_argument("--concurrency", type=int, default=16,
                   help="Max concurrent in-flight taxa (default: 16). Each consumes ~17 API calls in parallel internally.")
    p.add_argument("--min-interval", type=float, default=0.1,
                   help="Min seconds between any two HTTP requests (default: 0.1)")
    p.add_argument("--max-depth", type=int, default=99, help="Max recursion depth (default: 99 = unlimited)")
    p.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    p.add_argument("--max-retries", type=int, default=5, help="HTTP retries on 5xx/timeout")
    p.add_argument("--gzip", action="store_true", help="Gzip the output file when done")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    return Config(
        root=args.root,
        out=args.out,
        concurrency=args.concurrency,
        min_interval=args.min_interval,
        max_depth=args.max_depth,
        timeout=args.timeout,
        max_retries=args.max_retries,
    ), args.gzip


def main() -> int:
    cfg, do_gzip = parse_args()
    log.info("WoRMS dump starting: root=%d out=%s concurrency=%d interval=%.2fs",
             cfg.root, cfg.out, cfg.concurrency, cfg.min_interval)
    conn = open_db(cfg.out)
    try:
        asyncio.run(crawl(cfg, conn))
    finally:
        conn.close()
    if do_gzip:
        log.info("compressing -> %s.gz", cfg.out)
        out_gz = gzip_file(cfg.out)
        log.info("done: %s (%.1f MB)", out_gz, out_gz.stat().st_size / 1e6)
    return 0


if __name__ == "__main__":
    sys.exit(main())
