from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings

_logger = structlog.get_logger()

_POOL_MIN = 10
_POOL_MAX = 50

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = Settings()
        _engine = create_async_engine(
            str(settings.database_url),
            echo=settings.echo_sql,
            pool_size=_POOL_MIN,
            max_overflow=_POOL_MAX - _POOL_MIN,
        )
        _logger.info(
            "db.engine_created",
            pool_min=_POOL_MIN,
            pool_max=_POOL_MAX,
            echo_sql=settings.echo_sql,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _session_maker


# Convenience module-level exports (lazily resolved at call time)
def _engine_accessor() -> AsyncEngine:
    return _get_engine()


async_session_maker = get_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    maker = get_session_maker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
