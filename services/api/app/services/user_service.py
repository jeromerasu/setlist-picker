from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.hashing import dummy_verify, hash_password, verify_password
from app.auth.palette import AVATAR_PALETTE
from app.db.models.user import User
from app.db.uuid7 import uuid7
from app.schemas.auth import UserCreate, UserUpdate

_logger = structlog.get_logger()


def _pick_avatar(user_id: uuid.UUID) -> str:
    return AVATAR_PALETTE[int(user_id) % len(AVATAR_PALETTE)]


async def create_local_user(db: AsyncSession, payload: UserCreate) -> User:
    email = payload.email.lower()
    user_id = uuid7()
    user = User(
        id=user_id,
        auth_provider="local",
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        avatar_color=_pick_avatar(user_id),
    )
    try:
        async with db.begin_nested():
            db.add(user)
            await db.flush()
    except IntegrityError as exc:
        detail = str(exc.orig) if exc.orig else str(exc)
        if "uq_user_email" in detail or "user_email" in detail.lower():
            raise ValueError("email_taken") from exc
        raise
    _logger.info("auth.user_created", user_id=str(user.id), auth_provider="local")
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(
        select(User).where(
            User.auth_provider == "local",
            User.email == email.lower(),
        )
    )
    user = result.scalar_one_or_none()
    if user is None or not user.password_hash:
        dummy_verify()
        _logger.warning(
            "auth.login_failed",
            email_attempted=email,
            reason="no_such_user",
        )
        raise ValueError("invalid_credentials")

    if not verify_password(password, user.password_hash):
        _logger.warning(
            "auth.login_failed",
            email_attempted=email,
            reason="bad_password",
        )
        raise ValueError("invalid_credentials")

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    _logger.info("auth.login_succeeded", user_id=str(user.id), auth_provider="local")
    return user


async def get_or_create_apple_user(
    db: AsyncSession,
    apple_sub: str,
    email: str | None,
    display_name: str | None,
) -> tuple[User, bool]:
    """Return (user, created). created=True on first sign-in."""
    result = await db.execute(select(User).where(User.apple_subject_id == apple_sub))
    user = result.scalar_one_or_none()
    if user is not None:
        user.last_login_at = datetime.now(timezone.utc)
        await db.flush()
        _logger.info("auth.apple_login", user_id=str(user.id))
        return user, False

    user_id = uuid7()
    user = User(
        id=user_id,
        auth_provider="apple",
        apple_subject_id=apple_sub,
        email=email,
        display_name=display_name,
        avatar_color=_pick_avatar(user_id),
    )
    db.add(user)
    await db.flush()
    _logger.info("auth.apple_user_created", user_id=str(user.id))
    return user, True


async def get_or_create_google_user(
    db: AsyncSession,
    google_sub: str,
    email: str | None,
    display_name: str | None,
) -> tuple[User, bool]:
    """Return (user, created). created=True on first sign-in."""
    result = await db.execute(select(User).where(User.google_subject_id == google_sub))
    user = result.scalar_one_or_none()
    if user is not None:
        user.last_login_at = datetime.now(timezone.utc)
        await db.flush()
        _logger.info("auth.google_login", user_id=str(user.id))
        return user, False

    user_id = uuid7()
    user = User(
        id=user_id,
        auth_provider="google",
        google_subject_id=google_sub,
        email=email,
        display_name=display_name,
        avatar_color=_pick_avatar(user_id),
    )
    db.add(user)
    await db.flush()
    _logger.info("auth.google_user_created", user_id=str(user.id))
    return user, True


async def patch_user(db: AsyncSession, user: User, payload: UserUpdate) -> User:
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.avatar_color is not None:
        user.avatar_color = payload.avatar_color
    if payload.email is not None:
        email = payload.email.lower()
        user.email = email

    user.updated_at = datetime.now(timezone.utc)
    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError as exc:
        detail = str(exc.orig) if exc.orig else str(exc)
        if "uq_user_email" in detail or "user_email" in detail.lower():
            raise ValueError("email_taken") from exc
        raise
    return user
