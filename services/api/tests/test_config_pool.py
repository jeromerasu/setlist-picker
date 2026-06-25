"""TASK-SETLIST-PERF-CONFIG: assert engine pool_size == 10, max_overflow == 40."""

from __future__ import annotations

from app.db.session import _get_engine


def test_engine_pool_size_is_10() -> None:
    engine = _get_engine()
    assert engine.pool.size() == 10  # type: ignore[attr-defined]


def test_engine_max_overflow_is_40() -> None:
    engine = _get_engine()
    assert engine.pool._max_overflow == 40  # type: ignore[attr-defined]
