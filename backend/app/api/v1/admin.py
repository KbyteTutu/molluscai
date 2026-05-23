from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date as date_type, datetime, timedelta, timezone

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Permission, RequirePermission
from app.api.v1.feedback import ALLOWED_CATEGORIES
from app.database import get_db
from app.models.user import User, RoleQuota, QueryLog
from app.models.auction import Auction
from app.models.feedback import Feedback
from app.tasks.auction_scraper import scrape_incremental
from app.tasks.embedding_job import embed_run, embed_cancel, auction_embed_run, auction_embed_cancel
from app.tasks.image_downloader import download_sold_images
from app.tasks.celery_app import celery_app
from app.services.minio_client import get_minio
from app.services.task_tracker import record_task, get_recent_tasks, get_task, get_worker_tasks
from app.core.security import hash_password
from app.core.request_ip import get_display_ip

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


@router.post("/embed/auction/run", response_model=TaskAck)
def run_auction_embed(
    payload: EmbedRequest,
    _: User = Depends(require_admin),
):
    async_result = auction_embed_run.delay(rebuild=payload.rebuild, limit=payload.limit)
    record_task(async_result.id, "auction.embed_run",
        {"rebuild": payload.rebuild, "limit": payload.limit})
    return TaskAck(task_id=async_result.id, task_name="auction.embed_run")


@router.post("/embed/auction/cancel", response_model=TaskAck)
def cancel_auction_embed(
    _: User = Depends(require_admin),
):
    async_result = auction_embed_cancel.delay()
    record_task(async_result.id, "auction.embed_cancel", {})
    return TaskAck(task_id=async_result.id, task_name="auction.embed_cancel")


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


class RoleQuotaOut(BaseModel):
    role: str
    daily_auction_limit: int
    daily_rag_limit: int
    daily_ai_limit: int
    daily_taxa_limit: int
    hourly_auction_limit: int
    hourly_ai_limit: int
    hourly_taxa_limit: int
    rate_limit_per_min: int

    model_config = {"from_attributes": True}


class RoleQuotaUpdate(BaseModel):
    daily_auction_limit: Optional[int] = Field(default=None, ge=-1)
    daily_rag_limit: Optional[int] = Field(default=None, ge=-1)
    daily_ai_limit: Optional[int] = Field(default=None, ge=-1)
    daily_taxa_limit: Optional[int] = Field(default=None, ge=-1)
    hourly_auction_limit: Optional[int] = Field(default=None, ge=-1)
    hourly_ai_limit: Optional[int] = Field(default=None, ge=-1)
    hourly_taxa_limit: Optional[int] = Field(default=None, ge=-1)
    rate_limit_per_min: Optional[int] = Field(default=None, ge=-1)


@router.get("/quotas", response_model=List[RoleQuotaOut])
async def list_quotas(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = await db.execute(select(RoleQuota).order_by(RoleQuota.role))
    return [RoleQuotaOut.model_validate(r) for r in rows.scalars().all()]


@router.patch("/quotas/{role}", response_model=RoleQuotaOut)
async def update_quota(
    role: str,
    payload: RoleQuotaUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    locked = await db.execute(
        select(RoleQuota).where(RoleQuota.role == role).with_for_update()
    )
    quota = locked.scalar_one_or_none()
    if quota is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role {role!r} not found")

    update_fields = payload.model_dump(exclude_unset=True)
    for k, v in update_fields.items():
        setattr(quota, k, v)
    await db.commit()
    await db.refresh(quota)
    return RoleQuotaOut.model_validate(quota)


class QueryStatsByType(BaseModel):
    query_type: str
    count: int


class QueryStatsByDay(BaseModel):
    day: str
    query_type: str
    count: int


class QueryStatsTopUser(BaseModel):
    user_id: Optional[str]
    username: Optional[str]
    count: int


class QueryStatsResponse(BaseModel):
    total: int
    rate_limited_429: int
    by_type: List[QueryStatsByType]
    by_day: List[QueryStatsByDay]
    top_users: List[QueryStatsTopUser]
    top_keywords: List[dict]
    range_days: int


@router.get("/queries/stats", response_model=QueryStatsResponse)
async def query_stats(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_row = await db.execute(
        select(func.count(QueryLog.id)).where(QueryLog.created_at >= since)
    )
    total = int(total_row.scalar_one() or 0)

    rl_row = await db.execute(
        select(func.count(QueryLog.id)).where(
            QueryLog.created_at >= since, QueryLog.status_code == 429
        )
    )
    rate_limited_429 = int(rl_row.scalar_one() or 0)

    by_type_rows = await db.execute(
        select(QueryLog.query_type, func.count(QueryLog.id))
        .where(QueryLog.created_at >= since)
        .group_by(QueryLog.query_type)
        .order_by(func.count(QueryLog.id).desc())
    )
    by_type = [
        QueryStatsByType(query_type=qt or "unknown", count=int(c))
        for qt, c in by_type_rows.all()
    ]

    by_day_rows = await db.execute(
        text("""
            SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
                   COALESCE(query_type, 'unknown') AS query_type,
                   COUNT(*) AS n
            FROM query_logs
            WHERE created_at >= :since
            GROUP BY 1, 2
            ORDER BY 1 ASC, 2 ASC
        """),
        {"since": since},
    )
    by_day = [
        QueryStatsByDay(day=r.day, query_type=r.query_type, count=int(r.n))
        for r in by_day_rows
    ]

    top_users_rows = await db.execute(
        text("""
            SELECT q.user_id::text AS user_id, u.username, COUNT(*) AS n
            FROM query_logs q
            LEFT JOIN users u ON u.id = q.user_id
            WHERE q.created_at >= :since AND q.user_id IS NOT NULL
            GROUP BY q.user_id, u.username
            ORDER BY n DESC
            LIMIT 10
        """),
        {"since": since},
    )
    top_users = [
        QueryStatsTopUser(user_id=r.user_id, username=r.username, count=int(r.n))
        for r in top_users_rows
    ]

    top_keywords_rows = await db.execute(
        text("""
            SELECT lower(query_text) AS kw, COUNT(*) AS n
            FROM query_logs
            WHERE created_at >= :since
              AND query_text IS NOT NULL
              AND query_text != ''
              AND length(query_text) BETWEEN 2 AND 100
              AND query_type IN ('taxa', 'ai')
            GROUP BY 1
            ORDER BY n DESC
            LIMIT 10
        """),
        {"since": since},
    )
    top_keywords = [{"keyword": r.kw, "count": int(r.n)} for r in top_keywords_rows]

    return QueryStatsResponse(
        total=total,
        rate_limited_429=rate_limited_429,
        by_type=by_type,
        by_day=by_day,
        top_users=top_users,
        top_keywords=top_keywords,
        range_days=days,
    )


class QueryLogOut(BaseModel):
    id: int
    user_id: Optional[str]
    username: Optional[str]
    query_text: str
    query_type: Optional[str]
    result_count: Optional[int]
    cost: float
    ip_address: Optional[str]
    display_ip: Optional[str] = None
    status_code: int
    created_at: str


@router.get("/queries/recent", response_model=List[QueryLogOut])
async def query_recent(
    limit: int = 100,
    q: str = Query(default="", description="Filter by query_text (ILIKE substring match)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    limit = max(1, min(int(limit or 100), 500))
    q_filter = q.strip()
    where_clause = ""
    params: dict = {"limit": limit}
    if q_filter:
        where_clause = "WHERE q.query_text ILIKE :q"
        params["q"] = f"%{q_filter}%"
    rows = await db.execute(
        text(f"""
            SELECT q.id, q.user_id::text AS user_id, u.username,
                   q.query_text, q.query_type, q.result_count,
                   COALESCE(q.cost, 0)::float AS cost,
                   q.ip_address::text AS ip_address,
                   COALESCE(q.status_code, 200) AS status_code,
                   q.created_at
            FROM query_logs q
            LEFT JOIN users u ON u.id = q.user_id
            {where_clause}
            ORDER BY q.id DESC
            LIMIT :limit
        """),
        params,
    )
    return [
        QueryLogOut(
            id=int(r.id),
            user_id=r.user_id,
            username=r.username,
            query_text=r.query_text,
            query_type=r.query_type,
            result_count=r.result_count,
            cost=float(r.cost or 0),
            ip_address=r.ip_address,
            display_ip=get_display_ip(r.ip_address),
            status_code=int(r.status_code),
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]


ALLOWED_ROLES = {"user", "vip", "doc_admin", "superadmin"}


class AdminUserOut(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    balance: float
    daily_query_limit: Optional[int]
    created_at: str


class AdminUserListResponse(BaseModel):
    items: List[AdminUserOut]
    total: int
    limit: int
    offset: int


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class AdminUserPasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


def _serialize_user(u: User) -> AdminUserOut:
    return AdminUserOut(
        id=str(u.id),
        username=u.username,
        email=u.email,
        role=u.role,
        is_active=bool(u.is_active),
        balance=float(u.balance or 0),
        daily_query_limit=u.daily_query_limit,
        created_at=u.created_at.isoformat() if u.created_at else "",
    )


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    q: Optional[str] = Query(default=None, description="search username or email"),
    role: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(User)
    count_stmt = select(func.count(User.id))

    if q:
        like = f"%{q.strip()}%"
        cond = (User.username.ilike(like)) | (User.email.ilike(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if role:
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail=f"Unknown role: {role}")
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
        count_stmt = count_stmt.where(User.is_active.is_(is_active))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return AdminUserListResponse(
        items=[_serialize_user(u) for u in rows],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    locked = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    target = locked.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    is_self = str(target.id) == str(actor.id)

    if "role" in fields:
        new_role = fields["role"]
        if new_role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail=f"Unknown role: {new_role}")
        if is_self and target.role == "superadmin" and new_role != "superadmin":
            raise HTTPException(status_code=400, detail="不能降级自己的超级管理员权限")
        target.role = new_role

    if "is_active" in fields:
        new_active = bool(fields["is_active"])
        if is_self and not new_active:
            raise HTTPException(status_code=400, detail="不能锁定自己的账号")
        target.is_active = new_active

    await db.commit()
    await db.refresh(target)
    return _serialize_user(target)


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    payload: AdminUserPasswordReset,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    locked = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    target = locked.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    target.password_hash = hash_password(payload.new_password)
    await db.commit()
    return {"ok": True, "user_id": str(target.id), "username": target.username}
class AdminFeedbackOut(BaseModel):
    id: int
    user_id: str
    username: Optional[str]
    email: Optional[str]
    category: str
    content: str
    status: str
    admin_note: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str
    updated_at: str


class AdminFeedbackListResponse(BaseModel):
    items: List[AdminFeedbackOut]
    total: int
    limit: int
    offset: int


class AdminFeedbackUpdate(BaseModel):
    status: Optional[str] = None
    admin_note: Optional[str] = None

    model_config = {"extra": "forbid"}


ALLOWED_FEEDBACK_STATUSES = {"open", "acknowledged", "closed"}


def _serialize_admin_feedback(fb: Feedback, u: Optional[User]) -> AdminFeedbackOut:
    return AdminFeedbackOut(
        id=fb.id,
        user_id=str(fb.user_id) if fb.user_id else "",
        username=u.username if u else None,
        email=u.email if u else None,
        category=fb.category,
        content=fb.content,
        status=fb.status,
        admin_note=fb.admin_note,
        ip_address=str(fb.ip_address) if fb.ip_address else None,
        user_agent=fb.user_agent,
        created_at=fb.created_at.isoformat() if fb.created_at else "",
        updated_at=fb.updated_at.isoformat() if fb.updated_at else "",
    )


@router.get("/feedbacks", response_model=AdminFeedbackListResponse)
async def list_feedbacks(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    base = select(Feedback)
    count_base = select(func.count(Feedback.id))

    if status_filter:
        base = base.where(Feedback.status == status_filter)
        count_base = count_base.where(Feedback.status == status_filter)
    if category:
        if category not in ALLOWED_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        base = base.where(Feedback.category == category)
        count_base = count_base.where(Feedback.category == category)

    total = (await db.execute(count_base)).scalar_one()
    base = base.order_by(Feedback.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(base)).scalars().all()

    user_ids = {fb.user_id for fb in rows}
    user_map = {}
    if user_ids:
        user_rows = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        user_map = {u.id: u for u in user_rows}

    return AdminFeedbackListResponse(
        items=[_serialize_admin_feedback(fb, user_map.get(fb.user_id)) for fb in rows],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.patch("/feedbacks/{feedback_id}", response_model=AdminFeedbackOut)
async def update_feedback(
    feedback_id: int,
    payload: AdminFeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    locked = await db.execute(
        select(Feedback)
        .where(Feedback.id == feedback_id)
        .with_for_update()
    )
    fb = locked.scalar_one_or_none()
    if fb is None:
        raise HTTPException(status_code=404, detail="Feedback not found")

    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "status" in fields:
        new_status = fields["status"]
        if new_status not in ALLOWED_FEEDBACK_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Allowed: {', '.join(sorted(ALLOWED_FEEDBACK_STATUSES))}",
            )
        fb.status = new_status

    if "admin_note" in fields:
        fb.admin_note = fields["admin_note"]

    fb.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(fb)

    user = None
    if fb.user_id:
        user_row = await db.execute(select(User).where(User.id == fb.user_id))
        user = user_row.scalar_one_or_none()

    return _serialize_admin_feedback(fb, user)
