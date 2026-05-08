from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auction import (
    AuctionDetail,
    AuctionRead,
    AuctionSearchRequest,
    SearchResponse,
)
from app.services.auction_service import get_auction_by_item_no, search_auctions

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    filters: AuctionSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search auction listings with optional filters.
    Supports ILIKE text search, trigram similarity on name,
    price range, date range, and pagination (max offset 500, max limit 50).
    """
    items, total = await search_auctions(db, filters)
    return SearchResponse(
        items=items,
        total=total,
        offset=filters.offset,
        limit=filters.limit,
    )


@router.get("/{item_no}", response_model=AuctionDetail)
async def get_detail(
    item_no: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single auction listing by its item number."""
    auction = await get_auction_by_item_no(db, item_no)
    if auction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction item_no={item_no} not found",
        )
    return auction
