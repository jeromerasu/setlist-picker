"""BE-018: admin token auth dependency tests."""

from __future__ import annotations

from httpx import AsyncClient

_ADMIN_TOKEN = "test-admin-token"  # matches Settings default
_SAMPLE_PAYLOAD = {
    "event_name": "Auth Test Fest",
    "start_date": "2026-07-24",
    "end_date": "2026-07-26",
    "timezone": "Europe/Brussels",
    "source_adapter": "manual",
    "external_id": "auth-test-fest",
    "performances": [
        {
            "id": "p1",
            "name": "Test Set",
            "artists": [{"id": "a1", "name": "Test Artist"}],
            "stage": {"id": "s1", "name": "Stage"},
            "date": "2026-07-24",
            "day": "FRIDAY",
            "startTime": "2026-07-24 14:00:00+02:00",
            "endTime": "2026-07-24 15:00:00+02:00",
        }
    ],
}


async def test_admin_token_present_passes(client: AsyncClient) -> None:
    r = await client.post(
        "/api/events/import",
        json=_SAMPLE_PAYLOAD,
        headers={"X-Admin-Token": _ADMIN_TOKEN},
    )
    assert r.status_code == 200


async def test_admin_token_missing_returns_401(client: AsyncClient) -> None:
    r = await client.post("/api/events/import", json=_SAMPLE_PAYLOAD)
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "admin_token_invalid"


async def test_admin_token_wrong_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/api/events/import",
        json=_SAMPLE_PAYLOAD,
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "admin_token_invalid"
