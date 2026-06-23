from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user
from app.db.models.device import Device
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import UserOut, UserUpdate
from app.schemas.devices import (
    DeviceOut,
    DevicePlatform,
    DeviceRegisterRequest,
    DeviceRevokeResponse,
    PushProvider,
)
from app.schemas.groups import MyGroupListResponse
from app.services.device_service import DeviceNotFoundError, register_device, revoke_device
from app.services.group_service import list_my_groups
from app.services.user_service import patch_user

router = APIRouter(prefix="/api/users", tags=["users"])


def _device_out(d: Device) -> DeviceOut:
    return DeviceOut(
        device_id=d.id,
        user_id=d.user_id,
        platform=DevicePlatform(d.platform),
        push_provider=PushProvider(d.push_provider),
        created_at=d.created_at,
        last_seen_at=d.last_seen_at,
        revoked_at=d.revoked_at,
    )


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        auth_provider=user.auth_provider,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        avatar_color=user.avatar_color,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/me", response_model=UserOut)
async def get_me(
    caller: Annotated[User, Depends(current_user)],
) -> UserOut:
    return _user_out(caller)


@router.get("/me/groups", response_model=MyGroupListResponse)
async def get_my_groups(
    caller: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MyGroupListResponse:
    return await list_my_groups(db, caller)


@router.patch("/me", response_model=UserOut)
async def patch_me(
    payload: UserUpdate,
    caller: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    try:
        user = await patch_user(db, caller, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc)}) from exc
    return _user_out(user)


@router.post("/me/devices", response_model=DeviceOut)
async def register_device_endpoint(
    payload: DeviceRegisterRequest,
    caller: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
) -> DeviceOut:
    device, is_new = await register_device(db, caller.id, payload)
    if is_new:
        response.status_code = 201
    return _device_out(device)


@router.delete("/me/devices/{device_id}", response_model=DeviceRevokeResponse)
async def revoke_device_endpoint(
    device_id: UUID,
    caller: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceRevokeResponse:
    try:
        device = await revoke_device(db, caller.id, device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error_code": "device_not_found"}) from exc
    revoked_at = device.revoked_at
    assert revoked_at is not None
    return DeviceRevokeResponse(device_id=device.id, revoked_at=revoked_at)
