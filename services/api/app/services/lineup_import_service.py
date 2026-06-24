from __future__ import annotations

import time
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist, ArtistSourceRef, SetArtist
from app.db.models.event import Event
from app.db.models.set_ import Set
from app.db.models.stage import Stage
from app.db.uuid7 import uuid7
from app.schemas.lineup import LineupImportRequest, LineupImportResponse, LineupSourceArtist
from app.services.artist_normalize import normalize

_logger = structlog.get_logger()

_DISPLAY_ORDER_INCREMENT = 10

_STAGE_COLORS: tuple[str, ...] = (
    "#ff4f9a",  # 0  stage.sherwood
    "#36c6ff",  # 1  stage.tripolee
    "#a06bff",  # 2  stage.ranch
    "#2dd4bf",  # 3  stage.cosmic
    "#ffd23f",  # 4  HUES[4] amber
    "#ff6a3d",  # 5  HUES[4] orange
    "#ff2d9b",  # 6  neon.pink
    "#28e0ff",  # 7  neon.cyan
    "#a78bfa",  # 8  neon.purple
    "#7b5cff",  # 9  neon.purpleDeep
    "#0e7c66",  # 10 HUES[3] forest
    "#5b1bd6",  # 11 neon.violetSat
    "#ff8ad6",  # 12 text.daySectionAccent
    "#1453d6",  # 13 neon.skyDeep
    "#cdb4fe",  # 14 neon.lilac
)


async def import_lineup(
    db: AsyncSession,
    payload: LineupImportRequest,
) -> LineupImportResponse:
    t0 = time.monotonic()
    _logger.info(
        "lineup.import_started",
        source_adapter=payload.source_adapter,
        event_name=payload.event_name,
        performances_count=len(payload.performances),
    )

    counts = {
        "stages_created": 0,
        "stages_updated": 0,
        "sets_created": 0,
        "sets_updated": 0,
        "artists_created": 0,
        "artists_linked": 0,
    }

    try:
        event = await _upsert_event(db, payload)

        # Cache: external_id → stage, and first-seen position (0-based) per stage.
        stage_cache: dict[str, Stage] = {}
        stage_order: dict[str, int] = {}

        for perf in payload.performances:
            if perf.stage.id not in stage_order:
                stage_order[perf.stage.id] = len(stage_order)
            stage = await _upsert_stage(
                db, event, perf.stage.id, perf.stage.name, stage_cache, counts,
                position=stage_order[perf.stage.id],
            )

            starts_at = datetime.fromisoformat(perf.startTime)
            ends_at = datetime.fromisoformat(perf.endTime)

            set_obj, set_created = await _upsert_set(
                db,
                event,
                stage,
                external_id=perf.id,
                display_name=perf.name,
                day_label=perf.day,
                starts_at=starts_at,
                ends_at=ends_at,
            )
            if set_created:
                counts["sets_created"] += 1
            else:
                counts["sets_updated"] += 1

            for position, src_artist in enumerate(perf.artists):
                artist = await _upsert_artist(db, src_artist, payload.source_adapter, counts)
                await _upsert_set_artist(db, set_obj, artist, position)

        await db.flush()

        duration_ms = int((time.monotonic() - t0) * 1000)
        _logger.info(
            "lineup.import_complete",
            event_id=str(event.event_id),
            counts=counts,
            duration_ms=duration_ms,
        )

        return LineupImportResponse(
            event_id=event.event_id,
            stages_created=counts["stages_created"],
            stages_updated=counts["stages_updated"],
            sets_created=counts["sets_created"],
            sets_updated=counts["sets_updated"],
            artists_created=counts["artists_created"],
            artists_linked=counts["artists_linked"],
            imported_at=datetime.now(timezone.utc),
        )

    except SQLAlchemyError as exc:
        _logger.exception(
            "lineup.import_failed",
            source_adapter=payload.source_adapter,
            external_id=payload.external_id,
            exception_type=type(exc).__name__,
        )
        raise


async def _upsert_event(db: AsyncSession, payload: LineupImportRequest) -> Event:
    if payload.external_id is not None:
        stmt = (
            pg_insert(Event)
            .values(
                event_id=uuid7(),
                name=payload.event_name,
                start_date=payload.start_date,
                end_date=payload.end_date,
                timezone=payload.timezone,
                location=payload.location,
                source_adapter=payload.source_adapter,
                external_id=payload.external_id,
            )
            .on_conflict_do_update(
                index_elements=["source_adapter", "external_id"],
                index_where=Event.external_id.is_not(None),
                set_=dict(
                    name=pg_insert(Event).excluded.name,
                    start_date=pg_insert(Event).excluded.start_date,
                    end_date=pg_insert(Event).excluded.end_date,
                    timezone=pg_insert(Event).excluded.timezone,
                    location=pg_insert(Event).excluded.location,
                    imported_at=func.now(),
                ),
            )
            .returning(Event.event_id)
        )
        result = await db.execute(stmt)
        event_id = result.scalar_one()
        event_result = await db.execute(
            select(Event)
            .where(Event.event_id == event_id)
            .execution_options(populate_existing=True)
        )
        return event_result.scalar_one()
    else:
        event = Event(
            name=payload.event_name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            timezone=payload.timezone,
            location=payload.location,
            source_adapter=payload.source_adapter,
        )
        db.add(event)
        await db.flush()
        return event


async def _upsert_stage(
    db: AsyncSession,
    event: Event,
    external_id: str,
    name: str,
    cache: dict[str, Stage],
    counts: dict[str, int],
    position: int,
) -> Stage:
    if external_id in cache:
        return cache[external_id]

    existing_result = await db.execute(
        select(Stage).where(Stage.event_id == event.event_id, Stage.external_id == external_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        counts["stages_updated"] += 1
        cache[external_id] = existing
        return existing

    # New stage: display_order = current_max + increment
    max_result = await db.execute(
        select(func.max(Stage.display_order)).where(Stage.event_id == event.event_id)
    )
    current_max: int = max_result.scalar_one() or 0
    display_order = current_max + _DISPLAY_ORDER_INCREMENT
    stage = Stage(
        event_id=event.event_id,
        name=name,
        display_order=display_order,
        external_id=external_id,
        color_hex=_STAGE_COLORS[position % len(_STAGE_COLORS)],
    )
    db.add(stage)
    await db.flush()
    counts["stages_created"] += 1
    cache[external_id] = stage
    return stage


async def _upsert_set(
    db: AsyncSession,
    event: Event,
    stage: Stage,
    *,
    external_id: str,
    display_name: str,
    day_label: str,
    starts_at: datetime,
    ends_at: datetime,
) -> tuple[Set, bool]:
    existing_result = await db.execute(
        select(Set).where(Set.event_id == event.event_id, Set.external_id == external_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        existing.display_name = display_name
        existing.day_label = day_label
        existing.starts_at = starts_at
        existing.ends_at = ends_at
        await db.flush()
        return existing, False

    set_obj = Set(
        event_id=event.event_id,
        stage_id=stage.stage_id,
        display_name=display_name,
        day_label=day_label,
        starts_at=starts_at,
        ends_at=ends_at,
        external_id=external_id,
    )
    db.add(set_obj)
    await db.flush()
    return set_obj, True


async def _upsert_artist(
    db: AsyncSession,
    src: LineupSourceArtist,
    source_adapter: str,
    counts: dict[str, int],
) -> Artist:
    name_normalized = normalize(src.name)

    existing_result = await db.execute(
        select(Artist).where(Artist.name_normalized == name_normalized)
    )
    existing = existing_result.scalar_one_or_none()

    social_links: dict[str, str] = {}
    for field in ("instagram", "soundcloud", "tiktok", "twitter", "facebook", "youtube", "website"):
        val = getattr(src, field)
        if val is not None:
            social_links[field] = val

    if existing is not None:
        # trust-latest-non-null
        if src.spotify is not None:
            if existing.spotify_artist_id is not None and existing.spotify_artist_id != src.spotify:
                _logger.info(
                    "lineup.artist_spotify_id_changed",
                    artist_id=str(existing.artist_id),
                    old=existing.spotify_artist_id,
                    new=src.spotify,
                )
            existing.spotify_artist_id = src.spotify
        else:
            if existing.spotify_artist_id is not None:
                _logger.debug(
                    "lineup.artist_spotify_id_preserved",
                    artist_id=str(existing.artist_id),
                )

        if src.image is not None:
            existing.image_url = src.image

        if social_links:
            merged = dict(existing.social_links or {})
            merged.update(social_links)
            existing.social_links = merged

        await _upsert_source_ref(db, existing, source_adapter, src.id)
        counts["artists_linked"] += 1
        return existing

    artist = Artist(
        name=src.name,
        name_normalized=name_normalized,
        spotify_artist_id=src.spotify,
        image_url=src.image,
        social_links=social_links or None,
    )
    db.add(artist)
    await db.flush()
    await _upsert_source_ref(db, artist, source_adapter, src.id)
    counts["artists_created"] += 1
    return artist


async def _upsert_source_ref(
    db: AsyncSession, artist: Artist, source_adapter: str, external_id: str
) -> None:
    stmt = (
        pg_insert(ArtistSourceRef)
        .values(
            artist_id=artist.artist_id,
            source_adapter=source_adapter,
            external_id=external_id,
        )
        .on_conflict_do_nothing()
    )
    await db.execute(stmt)


async def _upsert_set_artist(db: AsyncSession, set_obj: Set, artist: Artist, position: int) -> None:
    stmt = (
        pg_insert(SetArtist)
        .values(set_id=set_obj.set_id, artist_id=artist.artist_id, position=position)
        .on_conflict_do_update(
            index_elements=["set_id", "artist_id"],
            set_=dict(position=pg_insert(SetArtist).excluded.position),
        )
    )
    await db.execute(stmt)
