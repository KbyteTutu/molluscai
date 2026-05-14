from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # bcrypt silently truncates at 72 bytes; do it explicitly to avoid
    # newer bcrypt library raising ValueError on long passwords
    pwd_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(pwd_bytes)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt truncates at 72 bytes; explicitly truncate to match hash_password
    # and avoid newer bcrypt library raising ValueError on long passwords
    pwd_bytes = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(pwd_bytes, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": subject, "exp": expire, "type": "access"}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def verify_token(token: str, token_type: str = "access") -> dict[str, Any]:
    """Verify and decode a JWT token. Returns the payload dict.
    Raises JWTError if invalid/expired or wrong type."""
    secret = (
        settings.JWT_SECRET_KEY
        if token_type == "access"
        else settings.JWT_REFRESH_SECRET_KEY
    )
    payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != token_type:
        raise JWTError("Invalid token type")
    return payload
