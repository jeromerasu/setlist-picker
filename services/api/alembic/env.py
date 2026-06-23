from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

import structlog
from sqlalchemy.ext.asyncio import create_async_engine

# Import all models so Alembic can detect them
import app.db.models.artist  # noqa: F401
import app.db.models.artist_cache  # noqa: F401
import app.db.models.device  # noqa: F401
import app.db.models.event  # noqa: F401
import app.db.models.group  # noqa: F401
import app.db.models.group_activity  # noqa: F401
import app.db.models.member  # noqa: F401
import app.db.models.pick  # noqa: F401
import app.db.models.set_  # noqa: F401
import app.db.models.stage  # noqa: F401
import app.db.models.user  # noqa: F401
from alembic import context
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_logger = structlog.get_logger()


def get_url() -> str:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url", "")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = get_url()
    connectable = create_async_engine(url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        _logger.info("db.migration_complete")
    await connectable.dispose()


def do_run_migrations(connection: object) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
