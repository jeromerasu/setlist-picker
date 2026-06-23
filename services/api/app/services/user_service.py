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
    username = payload.username.lower()
    email = payload.email.lower() if payload.email else None
    user_id = uuid7()
    user = User(
        id=user_id,
        auth_provider="local",
        username=username,
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
        if "uq_user_username" in detail or "user_username" in detail.lower():
            raise ValueError("username_taken") from exc
        if "uq_user_email" in detail or "user_email" in detail.lower():
            raise ValueError("email_taken") from exc
        raise
    _logger.info("auth.user_created", user_id=str(user.id), auth_provider="local")
    return user


async def authenticate(db: AsyncSession, username: str, password: str) -> User:
    result = await db.execute(
        select(User).where(
            User.auth_provider == "local",
            User.username == username.lower(),
        )
    )
    user = result.scalar_one_or_none()
    if user is None or not user.password_hash:
        dummy_verify()
        _logger.warning(
            "auth.login_failed",
            username_attempted=username,
            reason="no_such_user",
        )
        raise ValueError("invalid_credentials")

    if not verify_password(password, user.password_hash):
        _logger.warning(
            "auth.login_failed",
            username_attempted=username,
            reason="bad_password",
        )
        raise ValueError("invalid_credentials")

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    _logger.info("auth.login_succeeded", user_id=str(user.id), auth_provider="local")
    return user


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
