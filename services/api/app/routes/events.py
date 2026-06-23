from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.events import EventLineupResponse, EventListResponse
from app.services.event_service import get_event_lineup, list_events

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
