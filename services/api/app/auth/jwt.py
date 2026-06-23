from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import Settings


class Claims(BaseModel):
    sub: str
    iat: int
    exp: int
    type: Literal["access", "refresh"]
    jti: str | None = None


def _settings() -> Settings:
    return Settings()


def encode_access(user_id: uuid.UUID) -> tuple[str, datetime]:
    cfg = _settings()
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = cfg.jwt_access_ttl_hours * 3600
    exp_dt = datetime.fromtimestamp(now + ttl, tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ttl,
        "type": "access",
    }
    token = jwt.encode(payload, cfg.jwt_secret.get_secret_value(), algorithm="HS256")
    return token, exp_dt


def encode_refresh(user_id: uuid.UUID) -> tuple[str, datetime, uuid.UUID]:
    cfg = _settings()
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = cfg.jwt_refresh_ttl_days * 86400
    jti = uuid.uuid4()
    exp_dt = datetime.fromtimestamp(now + ttl, tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ttl,
        "type": "refresh",
        "jti": str(jti),
    }
    token = jwt.encode(payload, cfg.jwt_secret.get_secret_value(), algorithm="HS256")
    return token, exp_dt, jti


def decode(token: str, expected_type: Literal["access", "refresh"]) -> Claims:
    cfg = _settings()
    try:
        raw = jwt.decode(token, cfg.jwt_secret.get_secret_value(), algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError(str(exc)) from exc
    claims = Claims.model_validate(raw)
    if claims.type != expected_type:
        raise ValueError(f"expected token type '{expected_type}', got '{claims.type}'")
    return claims
