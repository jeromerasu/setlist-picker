from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user
from app.auth.invite_code import normalize
from app.db.models.group import Group
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.picks import (
    PickCreate,
    PickRemoveRequest,
    PickResult,
    PickSyncRequest,
    PickSyncResponse,
)
from app.services.pick_service import upsert_pick, upsert_picks_batch

router = APIRouter(prefix="/api/groups", tags=["picks"])

_logger = structlog.get_logger()


async def _resolve_group(invite_code_raw: str, db: AsyncSession) -> Group:
    code = normalize(invite_code_raw.upper())
    result = await db.execute(select(Group).where(Group.invite_code == code))
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail={"error_code": "group_not_found"})
    return group


@router.post("/{invite_code}/picks", response_model=PickResult)
async def create_pick_endpoint(
    invite_code: str,
    payload: PickCreate,
    caller: Annotated[User, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> PickResult:
    group = await _resolve_group(invite_code, db)
    return await upsert_pick(db, caller, group, payload)


@router.post("/{invite_code}/picks/sync", response_model=PickSyncResponse)
async def sync_picks_endpoint(
    invite_code: str,
    payload: PickSyncRequest,
    caller: Annotated[User, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> PickSyncResponse:
    group = await _resolve_group(invite_code, db)
    results = await upsert_picks_batch(db, caller, group, payload.toggles)
    return PickSyncResponse(results=results)


@router.delete("/{invite_code}/picks/{set_id}", response_model=PickResult)
async def delete_pick_endpoint(
    invite_code: str,
    set_id: uuid.UUID,
    payload: PickRemoveRequest,
    caller: Annotated[User, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> PickResult:
    group = await _resolve_group(invite_code, db)
    tombstone = PickCreate(
        set_id=set_id,
        state="tombstoned",
        state_clock_ms=payload.state_clock_ms,
    )
    return await upsert_pick(db, caller, group, tombstone)
