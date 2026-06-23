from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.admin import current_admin
from app.auth.dependencies import current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.events import EventLineupResponse, EventListResponse
from app.schemas.lineup import LineupImportRequest, LineupImportResponse
from app.services.event_service import get_event_lineup, list_events
from app.services.lineup_import_service import import_lineup

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events", response_model=EventListResponse)
async def list_events_endpoint(
    q: Annotated[str | None, Query(max_length=80)] = None,
    caller: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> EventListResponse:
    items = await list_events(db, q)
    return EventListResponse(events=items)


@router.get("/events/{event_id}/lineup", response_model=EventLineupResponse)
async def get_event_lineup_endpoint(
    event_id: uuid.UUID,
    caller: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> EventLineupResponse:
    return await get_event_lineup(db, event_id)


@router.post("/events/import", response_model=LineupImportResponse)
async def import_lineup_endpoint(
    payload: LineupImportRequest,
    _admin: Annotated[None, Depends(current_admin)],
    db: AsyncSession = Depends(get_db),
) -> LineupImportResponse:
    try:
        return await import_lineup(db, payload)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "lineup_import_failed"},
        ) from exc
