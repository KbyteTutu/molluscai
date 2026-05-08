"""
FastAPI dependency injection for authentication, authorization, and quota checks.
Matches design.md section 5.1 exactly.
"""

from enum import Flag, auto
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import verify_token
from app.database import get_db
from app.models.user import QueryLog, RoleQuota, User

security_scheme = HTTPBearer()


# ─── Permission Flags ───────────────────────────────────────


class Permission(Flag):
    SEARCH_AUCTION = auto()
    SEARCH_RAG = auto()
    EXPORT = auto()
    ADVANCED_FILTER = auto()
    BATCH_QUERY = auto()
    MANAGE_DOCS = auto()
    MANAGE_USERS = auto()
    MANAGE_MODELS = auto()
    VIEW_USAGE = auto()


ROLE_PERMISSIONS: dict[str, Permission] = {
    "user": Permission.SEARCH_AUCTION | Permission.SEARCH_RAG,
    "vip": Permission.SEARCH_AUCTION
    | Permission.SEARCH_RAG
    | Permission.EXPORT
    | Permission.ADVANCED_FILTER
    | Permission.BATCH_QUERY,
    "doc_admin": Permission.SEARCH_AUCTION
    | Permission.SEARCH_RAG
    | Permission.EXPORT
    | Permission.MANAGE_DOCS,
    "superadmin": ~Permission(0),
}


# ─── Dependency Helpers ─────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT from Authorization Bearer header, fetch user from DB."""
    try:
        payload = verify_token(credentials.credentials, token_type="access")
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    return user


class RequirePermission:
    """Dependency callable that checks the current user has a given Permission flag."""

    def __init__(self, perm: Permission):
        self.perm = perm

    async def __call__(
        self, current_user: User = Depends(get_current_user)
    ) -> User:
        role_perms = ROLE_PERMISSIONS.get(current_user.role, Permission(0))
        if not (role_perms & self.perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user


# ─── Quota Check ────────────────────────────────────────────


async def count_today_queries(
    db: AsyncSession, user_id: str, query_type: str
) -> int:
    """Count queries of a given type made by the user today."""
    stmt = select(func.count(QueryLog.id)).where(
        QueryLog.user_id == user_id,
        QueryLog.query_type == query_type,
        func.date(QueryLog.created_at) == func.current_date(),
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def check_quota(
    user: User, query_type: str, db: AsyncSession
) -> None:
    """Check if the user has remaining daily quota for the given query type.
    Raises HTTPException 429 if quota exceeded."""
    quota = user.daily_query_limit
    if quota is None:
        role_quota_result = await db.execute(
            select(RoleQuota).where(RoleQuota.role == user.role)
        )
        role_quota = role_quota_result.scalar_one_or_none()
        if role_quota is None:
            return
        quota = (
            role_quota.daily_rag_limit
            if query_type == "rag"
            else role_quota.daily_auction_limit
        )
    if quota == -1:
        return  # Unlimited

    today_count = await count_today_queries(db, user.id, query_type)
    if today_count >= quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily {query_type} query limit reached ({quota} queries)",
        )
