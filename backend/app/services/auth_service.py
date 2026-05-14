from typing import Optional

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.user import AuthResponse, TokenResponse, UserCreate, UserRead


def _build_auth_response(user: User) -> AuthResponse:
    user_id_str = str(user.id)
    return AuthResponse(
        user=UserRead.model_validate(user),
        access_token=create_access_token(subject=user_id_str),
        refresh_token=create_refresh_token(subject=user_id_str),
    )


async def register_user(
    db: AsyncSession, payload: UserCreate
) -> AuthResponse:
    existing = await db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Username or email already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return _build_auth_response(user)


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[AuthResponse]:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return _build_auth_response(user)


async def refresh_access_token(
    db: AsyncSession, refresh_token_str: str
) -> Optional[TokenResponse]:
    try:
        payload = verify_token(refresh_token_str, token_type="refresh")
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None

    new_access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )
