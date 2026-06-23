"""Verify alembic upgrade → downgrade → upgrade is idempotent."""

from __future__ import annotations

import subprocess
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import TEST_DB_URL


async def _count_tables(url: str) -> int:
    engine = create_async_engine(url, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
                " WHERE c.relkind = 'r' AND n.nspname = 'public'"
                " AND c.relname != 'alembic_version'"
            )
        )
        count = result.scalar_one()
    await engine.dispose()
    return int(count)


def _run_alembic(cmd: list[str]) -> None:
    env = {"DATABASE_URL": TEST_DB_URL.replace("+asyncpg", "")}
    import os

    full_env = {**os.environ, **env}
    full_env["DATABASE_URL"] = TEST_DB_URL
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *cmd],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(__import__("pathlib").Path(__file__).parent.parent),
    )
    if result.returncode != 0:
        raise RuntimeError(f"alembic {' '.join(cmd)} failed:\n{result.stderr}")


async def test_upgrade_then_downgrade_then_upgrade() -> None:
    _run_alembic(["downgrade", "base"])
    count_after_down = await _count_tables(TEST_DB_URL)
    assert count_after_down == 0

    _run_alembic(["upgrade", "head"])
    count_after_up = await _count_tables(TEST_DB_URL)
    assert count_after_up == 13
