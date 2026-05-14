from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.taxon import TaxonRead, TaxonSearchResponse
from app.services.taxa_search import hybrid_search

router = APIRouter()

SEARCHABLE_RANKS = ["Species", "Genus", "Family", "Order", "Class", "Phylum", "Kingdom"]


@router.get("/search", response_model=TaxonSearchResponse)
async def search_taxa(
    q: str = Query("", description="Name fragment"),
    mode: str = Query("lexical", pattern="^(lexical|hybrid)$"),
    rank: str | None = Query(None),
    family: str | None = Query(None),
    genus: str | None = Query(None),
    offset: int = Query(0, ge=0, le=5000),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if mode == "hybrid" and q.strip():
        return await hybrid_search(
            db=db, user_id=current_user.id, q=q.strip(),
            rank=rank, family=family, genus=genus,
            offset=offset, limit=limit,
        )

    clauses: list[str] = []
    params: dict[str, object] = {"offset": offset, "limit": limit}

    if q and len(q.strip()) >= 2:
        clauses.append("(scientificname ILIKE :qlike OR scientificname % :q)")
        params["q"] = q.strip()
        params["qlike"] = f"{q.strip()}%"
    if rank:
        clauses.append("rank = :rank")
        params["rank"] = rank
    if family:
        clauses.append("family ILIKE :family")
        params["family"] = f"{family}%"
    if genus:
        clauses.append("genus ILIKE :genus")
        params["genus"] = f"{genus}%"

    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    order_sql = (
        "ORDER BY similarity(scientificname, :q) DESC, scientificname ASC"
        if q and len(q.strip()) >= 2
        else "ORDER BY scientificname ASC"
    )

    total_row = await db.execute(text(f"SELECT COUNT(*) AS n FROM taxa {where_sql}"), params)
    total = total_row.scalar_one()

    rows = await db.execute(
        text(f"""
            SELECT aphia_id, scientificname, authority, rank, status,
                valid_aphia_id, valid_name,
                kingdom, phylum, subphylum, class, subclass, infraclass,
                superorder, "order", suborder, infraorder, superfamily,
                family, genus, species_epithet,
                is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct,
                citation, url, data_source, last_synced_at
            FROM taxa {where_sql} {order_sql}
            OFFSET :offset LIMIT :limit
        """),
        params,
    )
    items = [dict(r._mapping) for r in rows]
    return TaxonSearchResponse(
        items=[TaxonRead.model_validate(i) for i in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{aphia_id}", response_model=TaxonRead)
async def get_taxon(
    aphia_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = await db.execute(
        text("""
            SELECT aphia_id, scientificname, authority, rank, status,
                valid_aphia_id, valid_name,
                kingdom, phylum, subphylum, class, subclass, infraclass,
                superorder, "order", suborder, infraorder, superfamily,
                family, genus, species_epithet,
                is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct,
                citation, url, data_source, last_synced_at
            FROM taxa WHERE aphia_id = :id
        """),
        {"id": aphia_id},
    )
    record = row.mappings().first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taxon not found")
    return TaxonRead.model_validate(dict(record))
