"""BE-020: device registration schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.schemas.auth import _Model


class DevicePlatform(str, Enum):
    ios = "ios"
    android = "android"


class PushProvider(str, Enum):
    expo = "expo"
    apns = "apns"
    fcm = "fcm"


class DeviceRegisterRequest(_Model):
    platform: DevicePlatform
    push_token: str = Field(min_length=1, max_length=4096)
    push_provider: PushProvider = PushProvider.expo


class DeviceOut(_Model):
    device_id: UUID
    user_id: UUID
    platform: DevicePlatform
    push_provider: PushProvider
    created_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None


class DeviceRevokeResponse(_Model):
    device_id: UUID
    revoked_at: datetime
