from __future__ import annotations

from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user
from app.auth.invite_code import normalize
from app.db.models.group import Group
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.groups import (
    GroupCreate,
    GroupCreateResponse,
    GroupJoinRequest,
    GroupJoinResponse,
    GroupStateResponse,
)
from app.schemas.snapshot import GroupSnapshotResponse
from app.services.group_service import create_group, get_group_state, join_group
from app.services.snapshot_service import get_snapshot
from app.utils.http_dates import format_last_modified, parse_if_modified_since

_logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["groups"])


@router.post("/groups", response_model=GroupCreateResponse, status_code=201)
async def create_group_endpoint(
    payload: GroupCreate,
    caller: Annotated[User, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> GroupCreateResponse:
    return await create_group(db, caller, payload.name, payload.event_id)


@router.post("/groups/join", response_model=GroupJoinResponse)
async def join_group_endpoint(
    payload: GroupJoinRequest,
    caller: Annotated[User, Depends(current_user)],
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> GroupJoinResponse:
    result, is_new = await join_group(
        db, caller, payload.invite_code, payload.display_name_override
    )
    response.status_code = 201 if is_new else 200
    return result


@router.get("/groups/{invite_code}", response_model=GroupStateResponse)
async def get_group_state_endpoint(
    invite_code: str,
    request: Request,
    caller: Annotated[User, Depends(current_user)],
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> GroupStateResponse:
    from fastapi import HTTPException

    state = await get_group_state(db, caller, invite_code)
    # Floor to seconds — RFC 7231 If-Modified-Since has no sub-second resolution
    last_modified_dt = state.last_active_at.replace(microsecond=0)
    last_modified_str = format_last_modified(last_modified_dt)

    ims_header = request.headers.get("if-modified-since")
    if ims_header:
        ims_dt = parse_if_modified_since(ims_header)
        if ims_dt is not None and last_modified_dt <= ims_dt:
            raise HTTPException(
                status_code=304,
                headers={"Last-Modified": last_modified_str},
            )

    response.headers["Last-Modified"] = last_modified_str
    return state


async def _resolve_group_by_code(invite_code_raw: str, db: AsyncSession) -> Group:
    code = normalize(invite_code_raw.upper())
    result = await db.execute(select(Group).where(Group.invite_code == code))
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail={"error_code": "group_not_found"})
    return group


@router.get("/groups/{invite_code}/snapshot", response_model=GroupSnapshotResponse)
async def get_snapshot_endpoint(
    invite_code: str,
    request: Request,
    response: Response,
    caller: Annotated[User, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
    at: Annotated[datetime | None, Query()] = None,
    window_minutes: Annotated[int, Query(ge=5, le=360)] = 60,
) -> GroupSnapshotResponse:
    if at is None:
        raise HTTPException(status_code=400, detail={"error_code": "at_required"})

    group = await _resolve_group_by_code(invite_code, db)

    last_modified_dt = group.last_active_at.replace(microsecond=0)
    last_modified_str = format_last_modified(last_modified_dt)

    ims_header = request.headers.get("if-modified-since")
    if ims_header:
        ims_dt = parse_if_modified_since(ims_header)
        if ims_dt is not None and last_modified_dt <= ims_dt:
            _logger.debug("snapshot.served_304", group_id=str(group.id))
            raise HTTPException(
                status_code=304,
                headers={"Last-Modified": last_modified_str},
            )

    snap = await get_snapshot(db, caller, group, at, window_minutes)
    response.headers["Last-Modified"] = last_modified_str
    return snap
