from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.inaturalist import InatResult, lookup as inat_lookup


@dataclass(frozen=True)
class InatSyncResult:
    result: InatResult
    api_called: bool


async def load_cached_inaturalist(db: AsyncSession, aphia_id: int) -> InatResult | None:
    meta_row = await db.execute(
        text("""
            SELECT found, inat_id, preferred_common_name, observations_count,
                   wikipedia_url, wikipedia_summary, image_url, conservation_status
            FROM taxa_inaturalist WHERE aphia_id = :id
        """),
        {"id": aphia_id},
    )
    meta = meta_row.mappings().first()
    if not meta:
        return None
    if not meta["found"]:
        return InatResult(found=False)

    vernacular_rows = await db.execute(
        text("""
            SELECT vernacular, language_code
            FROM taxa_vernaculars
            WHERE aphia_id = :id AND source = 'inaturalist'
            ORDER BY language_code, vernacular
        """),
        {"id": aphia_id},
    )
    vernaculars = [dict(r._mapping) for r in vernacular_rows]
    return InatResult(
        found=True,
        inat_id=meta["inat_id"],
        preferred_common_name=meta["preferred_common_name"],
        observations_count=meta["observations_count"],
        wikipedia_url=meta["wikipedia_url"],
        wikipedia_summary=meta["wikipedia_summary"],
        image_url=meta["image_url"],
        conservation_status=meta["conservation_status"],
        vernaculars=vernaculars,
    )


async def store_inaturalist_result(db: AsyncSession, aphia_id: int, result: InatResult) -> None:
    if not result.found:
        await db.execute(
            text("""
                INSERT INTO taxa_inaturalist (aphia_id, found, synced_at)
                VALUES (:id, FALSE, now())
                ON CONFLICT (aphia_id) DO UPDATE SET
                    found = FALSE, synced_at = now()
            """),
            {"id": aphia_id},
        )
        return

    await db.execute(
        text("""
            INSERT INTO taxa_inaturalist
                (aphia_id, found, inat_id, preferred_common_name, observations_count,
                 wikipedia_url, wikipedia_summary, image_url, conservation_status, raw)
            VALUES (:aphia_id, TRUE, :inat_id, :pref, :obs, :wiki_url, :wiki_sum, :img, :cons, :raw)
            ON CONFLICT (aphia_id) DO UPDATE SET
                found = TRUE,
                inat_id = EXCLUDED.inat_id,
                preferred_common_name = EXCLUDED.preferred_common_name,
                observations_count = EXCLUDED.observations_count,
                wikipedia_url = EXCLUDED.wikipedia_url,
                wikipedia_summary = EXCLUDED.wikipedia_summary,
                image_url = EXCLUDED.image_url,
                conservation_status = EXCLUDED.conservation_status,
                raw = EXCLUDED.raw,
                synced_at = now()
        """),
        {
            "aphia_id": aphia_id,
            "inat_id": result.inat_id,
            "pref": result.preferred_common_name,
            "obs": result.observations_count,
            "wiki_url": result.wikipedia_url,
            "wiki_sum": result.wikipedia_summary,
            "img": result.image_url,
            "cons": result.conservation_status,
            "raw": None,
        },
    )

    if result.vernaculars:
        langs = list({v["language_code"].upper() for v in result.vernaculars if v.get("language_code")})
        if langs:
            await db.execute(
                text("""
                    DELETE FROM taxa_vernaculars
                    WHERE aphia_id = :id AND UPPER(language_code) = ANY(:langs)
                """),
                {"id": aphia_id, "langs": langs},
            )
        for v in result.vernaculars:
            await db.execute(
                text("""
                    INSERT INTO taxa_vernaculars (aphia_id, vernacular, language_code, source)
                    VALUES (:aphia_id, :vernacular, :language_code, 'inaturalist')
                    ON CONFLICT DO NOTHING
                """),
                {
                    "aphia_id": aphia_id,
                    "vernacular": v["vernacular"],
                    "language_code": v["language_code"],
                },
            )


async def sync_taxon_inaturalist(
    db: AsyncSession,
    *,
    aphia_id: int,
    scientific_name: str,
    rank: str | None,
    refresh: bool = False,
) -> InatSyncResult:
    if not refresh:
        cached = await load_cached_inaturalist(db, aphia_id)
        if cached is not None:
            return InatSyncResult(result=cached, api_called=False)

    result = await inat_lookup(scientific_name, rank)
    await store_inaturalist_result(db, aphia_id, result)
    return InatSyncResult(result=result, api_called=True)
