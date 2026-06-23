from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db.uuid7 import uuid7


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid7())
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
