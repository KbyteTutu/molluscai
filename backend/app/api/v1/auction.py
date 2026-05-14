from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Permission, RequirePermission, check_quota, get_db
from app.models.user import User
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


@router.post("/search", response_model=SearchResponse)
async def search(
    filters: AuctionSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auction),
):
    await check_quota(current_user, "auction", db)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auction),
):
    auction = await get_auction_by_item_no(db, item_no)
    if auction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction item_no={item_no} not found",
        )
    return await match_auction_taxon(db=db, user_id=current_user.id, raw_name=auction.name or "")
