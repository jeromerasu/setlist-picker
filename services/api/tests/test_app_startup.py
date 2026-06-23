"""BE-011: app startup / middleware integration tests."""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


async def test_healthz_returns_ok() -> None:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_cors_header_present_when_configured() -> None:
    settings = Settings(cors_origins=["https://example.com"])
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.options(
            "/healthz",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert "access-control-allow-origin" in r.headers


async def test_cors_header_absent_when_not_configured() -> None:
    settings = Settings()  # cors_origins=[]
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/healthz", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in r.headers


async def test_request_id_header_always_present() -> None:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/healthz")
    assert "x-request-id" in r.headers
