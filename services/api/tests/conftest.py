from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models.event import Event
from app.db.session import get_db
from app.main import create_app

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:dev@localhost:5433/setlist_test",
)


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def test_session_maker(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with get_db overridden to use the transactional test session."""
    app = create_app()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest.fixture
async def db_session(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Yields a session that rolls back all changes after each test."""
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest.fixture
async def test_event(db_session: AsyncSession) -> Event:
    """A persisted Event row for use in group tests."""
    event = Event(
        name="Test Festival",
        start_date=date(2026, 6, 20),
        end_date=date(2026, 6, 22),
        location="San Francisco, CA",
        timezone="America/Los_Angeles",
        source_adapter="manual",
    )
    db_session.add(event)
    await db_session.flush()
    return event


async def signup_and_get_token(
    client: AsyncClient,
    email: str = "testuser@example.com",
    password: str = "correct horse",
) -> tuple[str, str]:
    """Sign up a user and return (access_token, user_id)."""
    r = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": password},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["id"]
