from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.taxon import (
    TaxonChild,
    TaxonClassificationStep,
    TaxonDistribution,
    TaxonExternalId,
    TaxonRead,
    TaxonSearchResponse,
    TaxonSynonym,
    TaxonVernacular,
)
from app.services.taxa_search import hybrid_search, lexical_search

router = APIRouter()

SEARCHABLE_RANKS = ["Species", "Genus", "Family", "Order", "Class", "Phylum", "Kingdom"]


@router.get("/search", response_model=TaxonSearchResponse)
async def search_taxa(
    q: str = Query("", description="Name fragment (matches scientific name, 曾用名/synonym, or vernacular)"),
    mode: str = Query("lexical", pattern="^(lexical|hybrid)$"),
    rank: str | None = Query(None),
    family: str | None = Query(None),
    genus: str | None = Query(None),
    status: str | None = Query(None, description="Filter by taxonomic status, e.g. 'accepted'"),
    offset: int = Query(0, ge=0, le=5000),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if mode == "hybrid" and q.strip():
        return await hybrid_search(
            db=db, user_id=current_user.id, q=q.strip(),
            rank=rank, family=family, genus=genus, status=status,
            offset=offset, limit=limit,
        )

    if q and len(q.strip()) >= 2:
        return await lexical_search(
            db=db, q=q.strip(),
            rank=rank, family=family, genus=genus, status=status,
            offset=offset, limit=limit,
        )

    clauses: list[str] = []
    params: dict[str, object] = {"offset": offset, "limit": limit}
    if rank:
        clauses.append("rank = :rank")
        params["rank"] = rank
    if family:
        clauses.append("family ILIKE :family")
        params["family"] = f"{family}%"
    if genus:
        clauses.append("genus ILIKE :genus")
        params["genus"] = f"{genus}%"
    if status:
        clauses.append("status = :status")
        params["status"] = status
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""

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
            FROM taxa {where_sql}
            ORDER BY scientificname ASC
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


@router.get("/{aphia_id}/synonyms", response_model=list[TaxonSynonym])
async def get_taxon_synonyms(
    aphia_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await db.execute(
        text("""
            SELECT synonym_aphia_id, scientificname, authority, status
            FROM taxa_synonyms
            WHERE aphia_id = :id
            ORDER BY scientificname
        """),
        {"id": aphia_id},
    )
    return [TaxonSynonym.model_validate(dict(r._mapping)) for r in rows]


@router.get("/{aphia_id}/vernaculars", response_model=list[TaxonVernacular])
async def get_taxon_vernaculars(
    aphia_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await db.execute(
        text("""
            SELECT vernacular, language_code
            FROM taxa_vernaculars
            WHERE aphia_id = :id
            ORDER BY language_code NULLS LAST, vernacular
        """),
        {"id": aphia_id},
    )
    return [TaxonVernacular.model_validate(dict(r._mapping)) for r in rows]


@router.get("/{aphia_id}/distributions", response_model=list[TaxonDistribution])
async def get_taxon_distributions(
    aphia_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await db.execute(
        text("""
            SELECT locality, higher_geography, establishment_means,
                   decimal_latitude, decimal_longitude, quality_status
            FROM taxa_distributions
            WHERE aphia_id = :id
            ORDER BY higher_geography NULLS LAST, locality NULLS LAST
        """),
        {"id": aphia_id},
    )
    return [TaxonDistribution.model_validate(dict(r._mapping)) for r in rows]


@router.get("/{aphia_id}/children", response_model=list[TaxonChild])
async def get_taxon_children(
    aphia_id: int,
    accepted_only: bool = Query(False, description="Only return children with status='accepted'"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    where = "WHERE parent_aphia_id = :id"
    params: dict[str, object] = {"id": aphia_id}
    if accepted_only:
        where += " AND status = 'accepted'"
    rows = await db.execute(
        text(f"""
            SELECT child_aphia_id, scientificname, rank, status
            FROM taxa_children
            {where}
            ORDER BY rank, scientificname
        """),
        params,
    )
    return [TaxonChild.model_validate(dict(r._mapping)) for r in rows]


@router.get("/{aphia_id}/classification", response_model=list[TaxonClassificationStep])
async def get_taxon_classification(
    aphia_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await db.execute(
        text("""
            SELECT ancestor_aphia_id, scientificname, rank, depth
            FROM taxa_classification
            WHERE aphia_id = :id
            ORDER BY depth DESC
        """),
        {"id": aphia_id},
    )
    return [TaxonClassificationStep.model_validate(dict(r._mapping)) for r in rows]


@router.get("/{aphia_id}/external-ids", response_model=list[TaxonExternalId])
async def get_taxon_external_ids(
    aphia_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await db.execute(
        text("""
            SELECT source, external_id
            FROM taxa_external_ids
            WHERE aphia_id = :id
            ORDER BY source, external_id
        """),
        {"id": aphia_id},
    )
    return [TaxonExternalId.model_validate(dict(r._mapping)) for r in rows]
