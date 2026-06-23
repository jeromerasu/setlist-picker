from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode
from app.db.models.user import User
from app.db.session import get_db

_logger = structlog.get_logger()


async def current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    def _reject(reason: str) -> HTTPException:
        _logger.warning("auth.token_rejected", reason=reason)
        return HTTPException(status_code=401, detail={"error_code": "invalid_token"})

    if not authorization:
        raise _reject("missing_header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise _reject("missing_header")

    token = parts[1]
    try:
        claims = decode(token, expected_type="access")
    except ValueError as exc:
        reason = "expired" if "expired" in str(exc).lower() else "bad_signature"
        raise _reject(reason) from exc

    try:
        user_id = uuid.UUID(claims.sub)
    except ValueError as exc:
        raise _reject("bad_signature") from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        _logger.warning("auth.token_rejected", reason="user_not_found")
        raise HTTPException(status_code=401, detail={"error_code": "user_not_found"})

    return user
