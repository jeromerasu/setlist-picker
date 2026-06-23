from __future__ import annotations

from typing import Any

import httpx
import structlog
from cachetools import TTLCache

_logger = structlog.get_logger()

_jwks_cache: TTLCache[str, list[dict[str, Any]]] = TTLCache(maxsize=8, ttl=3600)


async def fetch_jwks(url: str) -> list[dict[str, Any]]:
    """Fetch JWKS from url, cached per-url with a 1-hour TTL."""
    cached: list[dict[str, Any]] | None = _jwks_cache.get(url)
    if cached is not None:
        return cached
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    keys: list[dict[str, Any]] = resp.json()["keys"]
    _jwks_cache[url] = keys
    _logger.info("auth.jwks_refreshed", url=url, key_count=len(keys))
    return keys
