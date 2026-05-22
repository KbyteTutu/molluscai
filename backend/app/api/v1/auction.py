import json
from datetime import date, timedelta
from typing import Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    Permission,
    RequirePermission,
    get_current_user_optional,
    get_current_user,
)
from app.config import settings
from app.core.quota import (
    QUERY_TYPE_AI,
    QUERY_TYPE_AUCTION,
    check_quota,
    log_query,
)
from app.core.request_ip import get_client_ip
from app.database import get_db
from app.models.user import User
from app.models.auction import Auction
from app.schemas.auction import (
    AuctionDetail,
    AuctionRead,
    AuctionSearchRequest,
    SearchResponse,
)
from app.services.auction_service import get_auction_by_item_no, search_auctions
from app.services.auction_taxon_match import TaxonMatchResponse, match_auction_taxon

router = APIRouter()

require_auction = RequirePermission(Permission.SEARCH_AUCTION)

RECENT_LIMIT_HARD_CAP = 12
RECENT_CACHE_KEY_PREFIX = "molluscai:auction:recent:v2"
RECENT_CACHE_TTL = 60

_redis_pool: Optional[redis.ConnectionPool] = None


def _redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL, max_connections=5, decode_responses=True
        )
    return redis.Redis(connection_pool=_redis_pool)


def _last_month_range(today: Optional[date] = None) -> tuple[date, date]:
    today = today or date.today()
    first_of_this_month = today.replace(day=1)
    last_of_prev = first_of_this_month - timedelta(days=1)
    first_of_prev = last_of_prev.replace(day=1)
    return first_of_prev, last_of_prev


@router.get("/recent", response_model=SearchResponse)
async def recent_public(
    db: AsyncSession = Depends(get_db),
):
    date_from, date_to = _last_month_range()
    cache_key = f"{RECENT_CACHE_KEY_PREFIX}:{date_from.isoformat()}:{date_to.isoformat()}"

    try:
        cached = _redis().get(cache_key)
        if cached:
            return SearchResponse.model_validate(json.loads(cached))
    except Exception:
        cached = None

    filters = AuctionSearchRequest(
        offset=0,
        limit=RECENT_LIMIT_HARD_CAP,
        sort="price_desc",
        end_date_from=date_from,
        end_date_to=date_to,
    )
    items, total = await search_auctions(db, filters)
    response = SearchResponse(items=items, total=total, offset=0, limit=RECENT_LIMIT_HARD_CAP)

    try:
        _redis().setex(cache_key, RECENT_CACHE_TTL, response.model_dump_json())
    except Exception:
        pass

    return response


@router.post("/search", response_model=SearchResponse)
async def search(
    filters: AuctionSearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auction),
):
    await check_quota(
        db, current_user, QUERY_TYPE_AUCTION,
        request=request,
        query_text=filters.model_dump_json(exclude_none=True),
    )

    items: list = []
    total: int = 0
    status_code = 200
    try:
        items, total = await search_auctions(db, filters)
        return SearchResponse(items=items, total=total, offset=filters.offset, limit=filters.limit)
    except HTTPException as e:
        status_code = e.status_code
        raise
    except Exception:
        status_code = 500
        raise
    finally:
        if status_code < 500:
            await log_query(
                db,
                user=current_user,
                query_type=QUERY_TYPE_AUCTION,
                query_text=filters.model_dump_json(exclude_none=True),
                result_count=total,
                ip_address=get_client_ip(request),
                status_code=status_code,
            )


@router.get("/search", include_in_schema=False)
async def _search_method_not_allowed() -> None:
    # Guard against FastAPI matching GET /auction/{item_no} for the literal
    # path "/auction/search" and returning a misleading int_parsing 422.
    # The real endpoint is POST /auction/search.
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Method Not Allowed. Use POST /auction/search.",
        headers={"Allow": "POST"},
    )


@router.get("/families")
async def list_families(
    q: str = Query(default="", description="Filter by family name (ILIKE)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return distinct family names with record counts for autocomplete."""
    stmt = (
        select(Auction.family, func.count(Auction.id).label("n"))
        .where(Auction.family.isnot(None), Auction.family != "")
    )
    if q.strip():
        stmt = stmt.where(Auction.family.ilike(f"%{q.strip()}%"))
    stmt = stmt.group_by(Auction.family).order_by(func.count(Auction.id).desc()).limit(40)
    rows = await db.execute(stmt)
    return [{"family": r.family, "count": int(r.n)} for r in rows]


@router.get("/{item_no}", response_model=AuctionDetail)
async def get_detail(
    item_no: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auction),
):
    auction = await get_auction_by_item_no(db, item_no)
    if auction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction item_no={item_no} not found",
        )
    return auction


@router.get("/{item_no}/taxon-match", response_model=TaxonMatchResponse)
async def auction_taxon_match(
    item_no: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auction),
):
    await check_quota(
        db, current_user, QUERY_TYPE_AI,
        request=request,
        query_text=f"taxon-match item_no={item_no}",
    )

    auction = await get_auction_by_item_no(db, item_no)
    if auction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction item_no={item_no} not found",
        )

    status_code = 200
    result_count: Optional[int] = None
    try:
        result = await match_auction_taxon(db=db, user_id=current_user.id, raw_name=auction.name or "")
        if result.matched is not None:
            result_count = 1 + len(result.alternatives)
        else:
            result_count = len(result.alternatives)
        return result
    except HTTPException as e:
        status_code = e.status_code
        raise
    except Exception:
        status_code = 500
        raise
    finally:
        if status_code < 500:
            await log_query(
                db,
                user=current_user,
                query_type=QUERY_TYPE_AI,
                query_text=f"taxon-match item_no={item_no} name={auction.name or ''}"[:500],
                result_count=result_count,
                ip_address=get_client_ip(request),
                status_code=status_code,
            )
