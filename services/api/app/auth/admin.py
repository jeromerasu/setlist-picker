from __future__ import annotations

import secrets
from typing import Annotated

import structlog
from fastapi import Header, HTTPException

from app.config import Settings

_logger = structlog.get_logger()
_settings = Settings()


async def current_admin(
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    """Raise 401 unless X-Admin-Token matches settings.admin_token (constant-time compare)."""
    expected = _settings.admin_token.get_secret_value()
    if x_admin_token is None or not secrets.compare_digest(
        x_admin_token.encode(), expected.encode()
    ):
        _logger.warning("auth.admin_token_invalid")
        raise HTTPException(status_code=401, detail={"error_code": "admin_token_invalid"})
