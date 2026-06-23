from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.groups import (
    GroupCreate,
    GroupCreateResponse,
    GroupJoinRequest,
    GroupJoinResponse,
    GroupStateResponse,
)
from app.services.group_service import create_group, get_group_state, join_group
from app.utils.http_dates import format_last_modified, parse_if_modified_since

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
    last_modified_dt = state.last_active_at
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
