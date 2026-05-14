from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.api.deps import Permission, RequirePermission
from app.models.user import User
from app.tasks.auction_scraper import scrape_incremental
from app.tasks.embedding_job import embed_run, embed_cancel
from app.tasks.image_downloader import download_sold_images

router = APIRouter()

require_admin = RequirePermission(Permission.MANAGE_USERS)


class ScrapeRequest(BaseModel):
    batch_size: int = Field(default=200, ge=1, le=2000)
    start_id: Optional[int] = Field(default=None, ge=1)


class ImageDownloadRequest(BaseModel):
    batch_size: int = Field(default=50, ge=1, le=500)


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
    return TaskAck(task_id=async_result.id, task_name="auction.scrape_incremental")


@router.post("/scraper/download-images", response_model=TaskAck)
def run_image_download(
    payload: ImageDownloadRequest,
    _: User = Depends(require_admin),
):
    async_result = download_sold_images.delay(batch_size=payload.batch_size)
    return TaskAck(task_id=async_result.id, task_name="auction.download_images")


@router.post("/embed/run", response_model=TaskAck)
def run_embed(
    payload: EmbedRequest,
    _: User = Depends(require_admin),
):
    async_result = embed_run.delay(rebuild=payload.rebuild, limit=payload.limit)
    return TaskAck(task_id=async_result.id, task_name="taxa.embed_run")


@router.post("/embed/cancel", response_model=TaskAck)
def cancel_embed(
    _: User = Depends(require_admin),
):
    async_result = embed_cancel.delay()
    return TaskAck(task_id=async_result.id, task_name="taxa.embed_cancel")
