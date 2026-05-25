"""
Auction scraper — ports legacy/shellauction-net-tool/get_data.py to the new schema.

Scrapes shellauction.net detail pages and writes into the `auctions` table.
Idempotent: ON CONFLICT (item_no) DO UPDATE refreshes mutable fields.
"""
import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import aiohttp
import asyncpg
from bs4 import BeautifulSoup

from app.config import settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

DETAIL_URL = "https://shellauction.net/auction_shell.php?id={id}&pres=1"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MolluscAI/0.1; +https://molluscai.local)"
}


@dataclass
class BidItem:
    item_no: int = 0
    name: str = ""
    family: str = ""
    size: str = ""
    locality: str = ""
    note: str = ""
    seller: str = ""
    start_price: Optional[float] = None
    final_price: Optional[float] = None
    end_date_raw: str = ""
    buyer: str = ""
    images: List[str] = field(default_factory=list)


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    try:
        if "approx" in text:
            piece = text.split(" (approx. ")[1].split("€")[0]
        else:
            piece = text.split("€")[0]
        return float(piece.strip().replace(",", "."))
    except (IndexError, ValueError):
        return None


def parse_detail(html: str, item_id: int) -> Optional[BidItem]:
    if "ERROR NO LOT<br>" in html:
        return None
    soup = BeautifulSoup(html, "lxml")
    item = BidItem(item_no=item_id)

    img_start = soup.find(string="Item Images\n")
    img_end = soup.find(string="Item")
    if img_start and img_end:
        current = img_start.find_parent("tr")
        end_tr = img_end.find_parent("tr")
        seen_srcs: set[str] = set()
        while current and current != end_tr:
            for img in current.find_all("img", title=False):
                src = img.get("src")
                if src and src not in seen_srcs:
                    seen_srcs.add(src)
                    item.images.append(src)
            current = current.find_next_sibling("tr")

    def field_td(label: str):
        td = soup.find("td", string=label)
        return td.find_next_sibling("td") if td else None

    try:
        if (td := field_td("Family")):
            item.family = td.text.strip()
        if (td := field_td("Name")):
            item.name = td.text.strip()
        if (td := field_td("Size")):
            item.size = td.text.strip()
        if (td := field_td("Locality")):
            item.locality = td.text.strip()
        if (td := field_td("Note")):
            item.note = td.text.strip()
        if (td := field_td("Seller")):
            item.seller = td.text.strip().split("(")[0].strip()
        if (td := field_td("Start Price")):
            item.start_price = _parse_price(td.text)
        if (td := field_td("Current Price")):
            content = td.text.strip()
            item.final_price = _parse_price(content)
            marker = "offered by"
            if marker in content:
                item.buyer = content[content.find(marker) + len(marker):].split("\xa0")[0].strip()
        if (td := field_td("End")):
            item.end_date_raw = td.text.split(">")[0].strip()
    except AttributeError:
        return None

    if not item.name and not item.family:
        return None
    return item


def _parse_end_date(raw: str):
    if not raw or "..." in raw:
        return None
    try:
        return datetime.strptime(raw, "%d-%m-%Y").date()
    except ValueError:
        return None


async def _fetch_one(session: aiohttp.ClientSession, item_id: int, sem: asyncio.Semaphore) -> Optional[BidItem]:
    async with sem:
        try:
            async with session.get(DETAIL_URL.format(id=item_id)) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        except Exception as e:
            logger.warning("fetch %s failed: %s", item_id, e)
            return None
    return parse_detail(html, item_id)


async def _upsert(pool: asyncpg.Pool, item: BidItem) -> None:
    end_date = _parse_end_date(item.end_date_raw)
    await pool.execute(
        """
        INSERT INTO auctions (item_no, name, family, size, locality, note, seller,
                              start_price, final_price, end_date, buyer, images_origin)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        ON CONFLICT (item_no) DO UPDATE SET
            name = EXCLUDED.name,
            family = EXCLUDED.family,
            size = EXCLUDED.size,
            locality = EXCLUDED.locality,
            note = EXCLUDED.note,
            seller = EXCLUDED.seller,
            start_price = EXCLUDED.start_price,
            final_price = EXCLUDED.final_price,
            end_date = EXCLUDED.end_date,
            buyer = EXCLUDED.buyer,
            images_origin = EXCLUDED.images_origin
        """,
        item.item_no,
        item.name or None,
        item.family or None,
        item.size or None,
        item.locality or None,
        item.note or None,
        item.seller or None,
        item.start_price,
        item.final_price,
        end_date,
        item.buyer or None,
        item.images or None,
    )


async def _run_scraper(start_id: int, count: int, concurrency: int = 10) -> dict:
    pool = await asyncpg.create_pool(settings.DATABASE_URL_SYNC.replace("postgresql://", "postgresql://"))
    sem = asyncio.Semaphore(concurrency)
    fetched = 0
    saved = 0
    skipped = 0
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT, headers=HEADERS) as session:
            tasks = [_fetch_one(session, i, sem) for i in range(start_id, start_id + count)]
            for coro in asyncio.as_completed(tasks):
                item = await coro
                fetched += 1
                if item is None:
                    skipped += 1
                    continue
                try:
                    await _upsert(pool, item)
                    saved += 1
                except Exception:
                    logger.error("upsert %s failed: %s", item.item_no, traceback.format_exc())
                    skipped += 1
    finally:
        await pool.close()
    return {"fetched": fetched, "saved": saved, "skipped": skipped, "start_id": start_id, "count": count}


async def _get_max_item_no() -> int:
    conn = await asyncpg.connect(settings.DATABASE_URL_SYNC)
    try:
        result = await conn.fetchval("SELECT COALESCE(MAX(item_no), 0) FROM auctions")
        return int(result or 0)
    finally:
        await conn.close()


@celery_app.task(name="auction.scrape_incremental", bind=True, max_retries=0)
def scrape_incremental(self, batch_size: int = 200, start_id: Optional[int] = None) -> dict:
    """
    Incrementally scrape `batch_size` items starting after MAX(item_no) (or from `start_id`).
    Designed to run on Celery Beat (hourly). Safe to run concurrently with itself thanks to ON CONFLICT.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        resolved_start = start_id if start_id is not None else loop.run_until_complete(_get_max_item_no()) + 1
        result = loop.run_until_complete(_run_scraper(resolved_start, batch_size))
        logger.info("scrape_incremental result: %s", result)
        return result
    finally:
        loop.close()
