from typing import Optional, Tuple, List

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auction import Auction
from app.schemas.auction import AuctionDetail, AuctionRead, AuctionSearchRequest


async def search_auctions(
    db: AsyncSession, filters: AuctionSearchRequest
) -> Tuple[List[Auction], int]:
    """Build and execute an auction search query with optional filters.
    Returns (items, total_count).
    """
    conditions = []

    if filters.name:
        conditions.append(
            func.similarity(Auction.name, filters.name) > 0.1
        )
    if filters.family:
        conditions.append(Auction.family.ilike(f"%{filters.family}%"))
    if filters.size:
        conditions.append(Auction.size.ilike(f"%{filters.size}%"))
    if filters.locality:
        conditions.append(Auction.locality.ilike(f"%{filters.locality}%"))
    if filters.price_min is not None:
        conditions.append(Auction.final_price >= filters.price_min)
    if filters.price_max is not None:
        conditions.append(Auction.final_price <= filters.price_max)
    if filters.end_date_from:
        conditions.append(Auction.end_date >= filters.end_date_from)
    if filters.end_date_to:
        conditions.append(Auction.end_date <= filters.end_date_to)
    if filters.seller:
        conditions.append(Auction.seller.ilike(f"%{filters.seller}%"))
    if filters.is_sold is not None:
        conditions.append(Auction.is_sold == filters.is_sold)

    base_query = select(Auction)
    if conditions:
        base_query = base_query.where(*conditions)

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    sort_map = {
        "price_desc": Auction.final_price.desc().nullslast(),
        "price_asc": Auction.final_price.asc().nullslast(),
        "item_no_desc": Auction.item_no.desc(),
        "end_date_desc": Auction.end_date.desc().nullslast(),
    }
    order_by = sort_map.get(filters.sort, Auction.end_date.desc().nullslast())

    query = base_query.order_by(order_by).offset(filters.offset).limit(filters.limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return list(items), total


async def get_auction_by_item_no(
    db: AsyncSession, item_no: int
) -> Optional[Auction]:
    """Get a single auction by its item_no."""
    result = await db.execute(
        select(Auction).where(Auction.item_no == item_no)
    )
    return result.scalar_one_or_none()
