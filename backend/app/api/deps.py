from enum import Flag, auto
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.quota import check_quota, log_query
from app.core.security import verify_token
from app.database import get_db
from app.models.user import User

security_scheme = HTTPBearer()
optional_security_scheme = HTTPBearer(auto_error=False)


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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
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


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        payload = verify_token(credentials.credentials, token_type="access")
        user_id: Optional[str] = payload.get("sub")
    except JWTError:
        return None
    if user_id is None:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


class RequirePermission:
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


__all__ = [
    "Permission",
    "ROLE_PERMISSIONS",
    "RequirePermission",
    "check_quota",
    "log_query",
    "get_current_user",
    "get_current_user_optional",
    "get_db",
    "security_scheme",
]
