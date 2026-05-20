from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date as date_type

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Permission, RequirePermission
from app.database import get_db
from app.models.user import User
from app.models.auction import Auction
from app.tasks.auction_scraper import scrape_incremental
from app.tasks.embedding_job import embed_run, embed_cancel
from app.tasks.image_downloader import download_sold_images
from app.tasks.celery_app import celery_app
from app.services.minio_client import get_minio
from app.services.task_tracker import record_task, get_recent_tasks, get_task, get_worker_tasks

router = APIRouter()

require_admin = RequirePermission(Permission.MANAGE_USERS)


class ScrapeRequest(BaseModel):
    batch_size: int = Field(default=200, ge=1, le=2000)
    start_id: Optional[int] = Field(default=None, ge=1)


class ImageDownloadRequest(BaseModel):
    batch_size: int = Field(default=50, ge=1, le=500)
    item_no_from: Optional[int] = Field(default=None, ge=1)
    item_no_to: Optional[int] = Field(default=None, ge=1)


class EmbedRequest(BaseModel):
    rebuild: bool = False
    limit: Optional[int] = Field(default=None, ge=1)


class TaskAck(BaseModel):
    task_id: str
    task_name: str


@router.post("/scraper/run", response_model=TaskAck)
def run_scraper(
    payload: ScrapeRequest,
    _: User = Depends(require_admin),
):
    async_result = scrape_incremental.delay(
        batch_size=payload.batch_size,
        start_id=payload.start_id,
    )
    record_task(async_result.id, "auction.scrape_incremental",
        {"batch_size": payload.batch_size, "start_id": payload.start_id})
    return TaskAck(task_id=async_result.id, task_name="auction.scrape_incremental")


@router.post("/scraper/download-images", response_model=TaskAck)
def run_image_download(
    payload: ImageDownloadRequest,
    _: User = Depends(require_admin),
):
    async_result = download_sold_images.delay(
        batch_size=payload.batch_size,
        item_no_from=payload.item_no_from,
        item_no_to=payload.item_no_to,
    )
    record_task(async_result.id, "auction.download_images",
        {"batch_size": payload.batch_size})
    return TaskAck(task_id=async_result.id, task_name="auction.download_images")


@router.post("/embed/run", response_model=TaskAck)
def run_embed(
    payload: EmbedRequest,
    _: User = Depends(require_admin),
):
    async_result = embed_run.delay(rebuild=payload.rebuild, limit=payload.limit)
    record_task(async_result.id, "taxa.embed_run",
        {"rebuild": payload.rebuild, "limit": payload.limit})
    return TaskAck(task_id=async_result.id, task_name="taxa.embed_run")


@router.post("/embed/cancel", response_model=TaskAck)
def cancel_embed(
    _: User = Depends(require_admin),
):
    async_result = embed_cancel.delay()
    record_task(async_result.id, "taxa.embed_cancel", {})
    return TaskAck(task_id=async_result.id, task_name="taxa.embed_cancel")


class ScraperStats(BaseModel):
    total_records: int
    max_item_no: Optional[int]
    last_end_date: Optional[date_type]
    last_created_at: Optional[str]
    images_downloaded: int
    images_pending: int
    storage_size_mb: float


@router.get("/scraper/stats", response_model=ScraperStats)
async def scraper_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    total = (await db.execute(select(func.count()).select_from(Auction))).scalar_one()
    max_no = (await db.execute(select(func.max(Auction.item_no)))).scalar_one()
    last_date = (await db.execute(select(func.max(Auction.end_date)))).scalar_one()
    last_created = (await db.execute(select(func.max(Auction.created_at)))).scalar_one()
    imgs_done = (await db.execute(
        select(func.count()).select_from(Auction).where(
            Auction.images_local.isnot(None),
            func.cardinality(Auction.images_local) > 0,
        )
    )).scalar_one()
    imgs_pending = (await db.execute(
        select(func.count()).select_from(Auction).where(
            Auction.is_sold == True,
            Auction.images_origin.isnot(None),
            (Auction.images_local.is_(None)) | (func.cardinality(Auction.images_local) == 0),
        )
    )).scalar_one()

    size_mb = 0.0
    try:
        client = get_minio()
        if client.bucket_exists("auction-images"):
            total_bytes = sum(obj.size for obj in client.list_objects("auction-images", recursive=True))
            size_mb = round(total_bytes / (1024 * 1024), 2)
    except Exception:
        pass

    return ScraperStats(
        total_records=total,
        max_item_no=max_no,
        last_end_date=last_date,
        last_created_at=last_created.isoformat() if last_created else None,
        images_downloaded=imgs_done,
        images_pending=imgs_pending,
        storage_size_mb=size_mb,
    )


class TaskInfo(BaseModel):
    task_id: str
    task_name: str
    state: str
    args: Optional[dict] = None
    result: Optional[dict] = None
    date_created: Optional[str] = None
    date_done: Optional[str] = None


class TaskListResponse(BaseModel):
    tasks: List[TaskInfo]
    workers: Optional[dict] = None


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    limit: int = 50,
    _: User = Depends(require_admin),
):
    tasks = get_recent_tasks(limit)
    workers = get_worker_tasks()
    return TaskListResponse(
        tasks=[TaskInfo(**t) for t in tasks],
        workers={
            "active": sum(len(v) for v in workers.get("active", {}).values()),
            "scheduled": sum(len(v) for v in workers.get("scheduled", {}).values()),
            "reserved": sum(len(v) for v in workers.get("reserved", {}).values()),
        },
    )


@router.get("/tasks/{task_id}", response_model=TaskInfo)
def get_task_detail(
    task_id: str,
    _: User = Depends(require_admin),
):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskInfo(**task)


class RevokeResponse(BaseModel):
    task_id: str
    revoked: bool


@router.post("/tasks/{task_id}/revoke", response_model=RevokeResponse)
def revoke_task(
    task_id: str,
    _: User = Depends(require_admin),
):
    celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
    return RevokeResponse(task_id=task_id, revoked=True)
