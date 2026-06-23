from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.config import Settings
from app.logging import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.routes import auth, health, users

_logger = structlog.get_logger()


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()
    configure_logging(level=cfg.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        _logger.info("app.startup", env=cfg.env, log_level=cfg.log_level, version="0.1.0")
        yield
        _logger.info("app.shutdown")

    app = FastAPI(title="setlist-picker", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    return app


app = create_app()
