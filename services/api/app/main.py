from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings
from app.logging import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.routes import auth, events, groups, health, picks, users

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

    # Middleware stack (outermost → innermost in add_middleware order is reversed)
    if cfg.trusted_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=cfg.trusted_hosts)
    if cfg.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(groups.router)
    app.include_router(picks.router)
    app.include_router(events.router)
    return app


app = create_app()
