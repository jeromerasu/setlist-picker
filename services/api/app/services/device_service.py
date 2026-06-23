"""BE-020: push-token registration service."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.device import Device
from app.schemas.devices import DeviceRegisterRequest

_logger = structlog.get_logger()


class DeviceNotFoundError(Exception):
    def __init__(self, device_id: UUID) -> None:
        super().__init__(f"device not found: {device_id}")
        self.device_id = device_id


async def register_device(
    db: AsyncSession,
    user_id: UUID,
    req: DeviceRegisterRequest,
) -> tuple[Device, bool]:
    """Idempotent registration; returns (device, is_new)."""
    result = await db.execute(
        select(Device).where(Device.user_id == user_id, Device.push_token == req.push_token)
    )
    existing = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if req.push_provider.value != "expo":
        _logger.info(
            "device.unusual_provider",
            user_id=str(user_id),
            push_provider=req.push_provider.value,
        )

    if existing is not None:
        was_revoked = existing.revoked_at is not None
        existing.last_seen_at = now
        existing.revoked_at = None
        await db.flush()
        _logger.info(
            "device.registered",
            user_id=str(user_id),
            device_id=str(existing.id),
            platform=existing.platform,
            push_provider=existing.push_provider,
            was_revoked=was_revoked,
        )
        return existing, False

    device = Device(
        user_id=user_id,
        platform=req.platform.value,
        push_token=req.push_token,
        push_provider=req.push_provider.value,
        last_seen_at=now,
    )
    db.add(device)
    await db.flush()
    _logger.info(
        "device.registered",
        user_id=str(user_id),
        device_id=str(device.id),
        platform=device.platform,
        push_provider=device.push_provider,
        was_revoked=False,
    )
    return device, True


async def revoke_device(
    db: AsyncSession,
    user_id: UUID,
    device_id: UUID,
) -> Device:
    """Set revoked_at; idempotent. Raises DeviceNotFoundError if not owned by caller."""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user_id)
    )
    device = result.scalar_one_or_none()
    if device is None:
        raise DeviceNotFoundError(device_id)

    if device.revoked_at is None:
        device.revoked_at = datetime.now(timezone.utc)
        await db.flush()

    _logger.info("device.revoked", user_id=str(user_id), device_id=str(device_id))
    return device
