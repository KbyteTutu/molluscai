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
from app.schemas.user import TokenResponse, UserCreate


async def register_user(
    db: AsyncSession, payload: UserCreate
) -> TokenResponse:
    """Create a new user and return access + refresh tokens."""
    # Check for existing user
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

    user_id_str = str(user.id)
    access_token = create_access_token(subject=user_id_str)
    refresh_token = create_refresh_token(subject=user_id_str)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[TokenResponse]:
    """Authenticate a user by username and password. Returns tokens or None."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None

    user_id_str = str(user.id)
    access_token = create_access_token(subject=user_id_str)
    refresh_token = create_refresh_token(subject=user_id_str)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def refresh_access_token(
    db: AsyncSession, refresh_token_str: str
) -> Optional[TokenResponse]:
    """Validate refresh token and issue a new access + refresh token pair."""
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
