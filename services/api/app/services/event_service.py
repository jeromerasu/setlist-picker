from __future__ import annotations

import uuid as _uuid_mod

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist, SetArtist
from app.db.models.event import Event
from app.db.models.set_ import Set
from app.db.models.stage import Stage
from app.schemas.events import (
    ArtistRef,
    EventLineupResponse,
    EventListItem,
    SetDetail,
    StageDetail,
)

_logger = structlog.get_logger()

_Q_MAX_LEN = 80


def _escape_like(q: str) -> str:
    """Escape ILIKE special chars so user input is treated as literals."""
    return q.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


async def list_events(db: AsyncSession, q: str | None) -> list[EventListItem]:
    stripped = (q or "").strip()[:_Q_MAX_LEN]

    stmt = select(Event).order_by(Event.start_date.asc(), Event.name.asc())
    if stripped:
        pattern = f"%{_escape_like(stripped)}%"
        from sqlalchemy import or_

        stmt = stmt.where(or_(Event.name.ilike(pattern), Event.location.ilike(pattern)))

    result = await db.execute(stmt)
    events = result.scalars().all()

    _logger.debug(
        "events.listed",
        q=stripped or None,
        result_count=len(events),
    )

    return [
        EventListItem(
            event_id=e.event_id,
            name=e.name,
            start_date=e.start_date,
            end_date=e.end_date,
            location=e.location,
            timezone=e.timezone,
        )
        for e in events
    ]


async def get_event_lineup(db: AsyncSession, event_id: _uuid_mod.UUID) -> EventLineupResponse:
    event_result = await db.execute(select(Event).where(Event.event_id == event_id))
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail={"error_code": "event_not_found"})

    stages_result = await db.execute(
        select(Stage)
        .where(Stage.event_id == event_id)
        .order_by(Stage.display_order.asc(), Stage.name.asc())
    )
    stages = stages_result.scalars().all()

    sets_result = await db.execute(
        select(Set, SetArtist, Artist)
        .join(SetArtist, SetArtist.set_id == Set.set_id, isouter=True)
        .join(Artist, Artist.artist_id == SetArtist.artist_id, isouter=True)
        .where(Set.event_id == event_id)
        .order_by(Set.starts_at.asc(), Set.display_name.asc(), SetArtist.position.asc())
    )
    raw_rows = sets_result.all()

    # Collect set data, grouping artists per set
    sets_by_id: dict[_uuid_mod.UUID, tuple[Set, list[tuple[SetArtist, Artist | None]]]] = {}
    for s, sa, art in raw_rows:
        if s.set_id not in sets_by_id:
            sets_by_id[s.set_id] = (s, [])
        if sa is not None:
            sets_by_id[s.set_id][1].append((sa, art))

    set_count = len(sets_by_id)
    all_sets: list[SetDetail] = []
    for s, artist_pairs in sets_by_id.values():
        artist_refs = [
            ArtistRef(
                artist_id=art.artist_id,
                name=art.name,
                position=sa.position,
                spotify_artist_id=art.spotify_artist_id,
            )
            for sa, art in artist_pairs
            if art is not None
        ]
        artist_refs.sort(key=lambda a: a.position)
        if not artist_refs:
            _logger.warning(
                "event.set_without_artists",
                set_id=str(s.set_id),
                event_id=str(event_id),
            )
        all_sets.append(
            SetDetail(
                set_id=s.set_id,
                display_name=s.display_name,
                day_label=s.day_label,
                starts_at=s.starts_at,
                ends_at=s.ends_at,
                artists=artist_refs,
            )
        )

    all_sets.sort(key=lambda s: (s.starts_at, s.display_name))

    sets_by_stage: dict[_uuid_mod.UUID, list[SetDetail]] = {}
    for s_row, _ in sets_by_id.values():
        if s_row.stage_id not in sets_by_stage:
            sets_by_stage[s_row.stage_id] = []

    for s_detail in all_sets:
        s_row_orig = sets_by_id[s_detail.set_id][0]
        if s_row_orig.stage_id in sets_by_stage:
            sets_by_stage[s_row_orig.stage_id].append(s_detail)

    stage_details = [
        StageDetail(
            stage_id=st.stage_id,
            name=st.name,
            display_order=st.display_order,
            color_hex=st.color_hex,
            sets=sets_by_stage.get(st.stage_id, []),
        )
        for st in stages
    ]

    response_bytes = len(str({"stages": len(stage_details), "sets": set_count}).encode())
    _logger.debug(
        "event.lineup_served",
        event_id=str(event_id),
        stage_count=len(stage_details),
        set_count=set_count,
        bytes=response_bytes,
    )
    if response_bytes > 200_000:
        _logger.warning(
            "event.lineup_size_exceeded_budget",
            event_id=str(event_id),
            bytes=response_bytes,
        )

    return EventLineupResponse(
        event_id=event.event_id,
        name=event.name,
        start_date=event.start_date,
        end_date=event.end_date,
        location=event.location,
        timezone=event.timezone,
        stages=stage_details,
        sets=all_sets,
    )
