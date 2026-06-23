from __future__ import annotations

from typing import Any

import structlog
from jose import JWTError, jwk
from jose import jwt as jose_jwt
from pydantic import BaseModel

from app.auth.jwks import fetch_jwks
from app.config import Settings

_logger = structlog.get_logger()

_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleClaims(BaseModel):
    sub: str
    iss: str
    aud: str
    exp: int
    iat: int
    email: str | None = None


def _find_key(keys: list[dict[str, Any]], kid: str) -> dict[str, Any] | None:
    return next((k for k in keys if k.get("kid") == kid), None)


async def validate_google_id_token(token: str) -> GoogleClaims:
    cfg = Settings()
    try:
        header = jose_jwt.get_unverified_header(token)
    except JWTError as exc:
        raise ValueError("google_invalid_token") from exc

    kid: str = str(header.get("kid", ""))
    keys = await fetch_jwks(cfg.google_jwks_url)
    jwk_dict = _find_key(keys, kid)
    if jwk_dict is None:
        _logger.warning("auth.google_jwks_kid_not_found", kid=kid)
        raise ValueError("google_key_not_found")

    try:
        public_key = jwk.construct(jwk_dict, algorithm="RS256")
        raw = jose_jwt.decode(
            token,
            public_key.to_dict(),
            algorithms=["RS256"],
            audience=cfg.google_client_id,
        )
    except JWTError as exc:
        _logger.warning("auth.google_token_invalid", error=str(exc))
        raise ValueError("google_invalid_token") from exc

    claims = GoogleClaims.model_validate(raw)
    if claims.iss not in _GOOGLE_ISSUERS:
        raise ValueError("google_invalid_issuer")

    return claims
