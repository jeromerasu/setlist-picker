from __future__ import annotations

from httpx import AsyncClient

from app.main import create_app


async def test_healthz_returns_200_and_status_ok(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "setlist-picker-api"}


async def test_healthz_response_is_application_json(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.headers["content-type"].startswith("application/json")


def test_create_app_returns_fresh_instance() -> None:
    app1 = create_app()
    app2 = create_app()
    assert app1 is not app2
