"""BE-020: device push-token registration tests."""

from __future__ import annotations

import uuid

import httpx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.device import Device
from tests.conftest import signup_and_get_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PAYLOAD: dict[str, str] = {
    "platform": "ios",
    "push_token": "ExponentPushToken[abc123]",
    "push_provider": "expo",
}


async def _auth_headers(client: AsyncClient, suffix: str = "") -> dict[str, str]:
    token, _ = await signup_and_get_token(client, f"device_user_{suffix}@example.com")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/users/me/devices
# ---------------------------------------------------------------------------


async def test_register_new_device_returns_201(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client, "new")
    r = await client.post("/api/users/me/devices", json=_VALID_PAYLOAD, headers=headers)
    assert r.status_code == 201
    body = r.json()
    assert body["platform"] == "ios"
    assert body["push_provider"] == "expo"
    assert body["revoked_at"] is None
    device_id = uuid.UUID(body["device_id"])

    row = await db_session.get(Device, device_id)
    assert row is not None
    assert row.revoked_at is None


async def test_register_idempotent_returns_200_and_bumps_last_seen(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client, "idem")
    r1 = await client.post("/api/users/me/devices", json=_VALID_PAYLOAD, headers=headers)
    assert r1.status_code == 201
    seen1 = r1.json()["last_seen_at"]

    r2 = await client.post("/api/users/me/devices", json=_VALID_PAYLOAD, headers=headers)
    assert r2.status_code == 200
    seen2 = r2.json()["last_seen_at"]
    assert r2.json()["device_id"] == r1.json()["device_id"]
    # last_seen_at must be >= first registration
    assert seen2 >= seen1


async def test_register_revoked_token_re_activates(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client, "reactivate")
    r1 = await client.post("/api/users/me/devices", json=_VALID_PAYLOAD, headers=headers)
    assert r1.status_code == 201
    device_id = r1.json()["device_id"]

    # Revoke it
    r_del = await client.delete(f"/api/users/me/devices/{device_id}", headers=headers)
    assert r_del.status_code == 200
    assert r_del.json()["revoked_at"] is not None

    # Re-register same token → re-activate
    r2 = await client.post("/api/users/me/devices", json=_VALID_PAYLOAD, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["device_id"] == device_id
    assert r2.json()["revoked_at"] is None


async def test_register_apns_provider_logs_unusual_value(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, "apns")
    payload = {**_VALID_PAYLOAD, "push_provider": "apns"}
    r = await client.post("/api/users/me/devices", json=payload, headers=headers)
    # Unusual provider is accepted; log emitted at INFO (not asserted here)
    assert r.status_code == 201
    assert r.json()["push_provider"] == "apns"


async def test_register_invalid_platform_returns_422(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, "badplat")
    payload = {**_VALID_PAYLOAD, "platform": "windows"}
    r = await client.post("/api/users/me/devices", json=payload, headers=headers)
    assert r.status_code == 422


async def test_register_unauthenticated_returns_401() -> None:
    from app.main import app as _app

    transport = httpx.ASGITransport(app=_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as raw:
        r = await raw.post("/api/users/me/devices", json=_VALID_PAYLOAD)
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/users/me/devices/{device_id}
# ---------------------------------------------------------------------------


async def test_revoke_device_sets_revoked_at(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client, "revoke")
    r1 = await client.post("/api/users/me/devices", json=_VALID_PAYLOAD, headers=headers)
    assert r1.status_code == 201
    device_id = r1.json()["device_id"]

    r_del = await client.delete(f"/api/users/me/devices/{device_id}", headers=headers)
    assert r_del.status_code == 200
    body = r_del.json()
    assert body["device_id"] == device_id
    assert body["revoked_at"] is not None

    row = await db_session.get(Device, uuid.UUID(device_id))
    assert row is not None
    assert row.revoked_at is not None


async def test_revoke_unknown_device_returns_404(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, "unk")
    r = await client.delete(f"/api/users/me/devices/{uuid.uuid4()}", headers=headers)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "device_not_found"


async def test_revoke_other_users_device_returns_404(
    client: AsyncClient,
) -> None:
    headers_a = await _auth_headers(client, "otha")
    headers_b = await _auth_headers(client, "othb")

    r1 = await client.post("/api/users/me/devices", json=_VALID_PAYLOAD, headers=headers_a)
    assert r1.status_code == 201
    device_id = r1.json()["device_id"]

    # User B tries to delete User A's device
    r_del = await client.delete(f"/api/users/me/devices/{device_id}", headers=headers_b)
    assert r_del.status_code == 404
    assert r_del.json()["detail"]["error_code"] == "device_not_found"


async def test_revoke_already_revoked_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client, "idem2")
    r1 = await client.post("/api/users/me/devices", json=_VALID_PAYLOAD, headers=headers)
    assert r1.status_code == 201
    device_id = r1.json()["device_id"]

    r_del1 = await client.delete(f"/api/users/me/devices/{device_id}", headers=headers)
    assert r_del1.status_code == 200
    revoked_at_first = r_del1.json()["revoked_at"]

    r_del2 = await client.delete(f"/api/users/me/devices/{device_id}", headers=headers)
    assert r_del2.status_code == 200
    # revoked_at must not change on second delete
    assert r_del2.json()["revoked_at"] == revoked_at_first
