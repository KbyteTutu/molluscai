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
from app.schemas.user import AuthResponse, PasswordChange, TokenResponse, UserCreate, UserRead


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
    # Login accepts either a username or an email in the same field.
    # We branch on '@' so callers don't need to tell us which one they sent.
    if "@" in username:
        stmt = select(User).where(User.email == username)
    else:
        stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
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


async def change_password(
    db: AsyncSession, user: User, payload: PasswordChange
) -> None:
    if not verify_password(payload.old_password, user.password_hash):
        raise ValueError("Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    await db.flush()
