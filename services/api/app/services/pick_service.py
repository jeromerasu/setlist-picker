from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.group import Group
from app.db.models.member import Member
from app.db.models.pick import Pick
from app.db.models.set_ import Set
from app.db.models.user import User
from app.schemas.picks import PickCreate, PickResult, PickState
from app.services.activity_service import ActivityKind, log_activity

_logger = structlog.get_logger()

_CLOCK_SKEW_BUFFER_MS = 3_600_000


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


async def _resolve_member(db: AsyncSession, caller: User, group: Group) -> Member:
    result = await db.execute(
        select(Member).where(Member.user_id == caller.id, Member.group_id == group.id)
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=403, detail={"error_code": "not_a_member"})
    return member


async def _validate_set_in_event(
    db: AsyncSession, set_id: uuid.UUID, event_id: uuid.UUID, group_id: uuid.UUID
) -> bool:
    result = await db.execute(select(Set).where(Set.set_id == set_id, Set.event_id == event_id))
    if result.scalar_one_or_none() is None:
        _logger.warning(
            "pick.set_id_not_in_event",
            group_id=str(group_id),
            set_id=str(set_id),
        )
        return False
    return True


async def upsert_pick(
    db: AsyncSession,
    caller: User,
    group: Group,
    payload: PickCreate,
) -> PickResult:
    server_now_ms = _now_ms()
    if payload.state_clock_ms > server_now_ms + _CLOCK_SKEW_BUFFER_MS:
        _logger.warning(
            "pick.clock_skew_rejected",
            group_id=str(group.id),
            set_id=str(payload.set_id),
            incoming_clock_ms=payload.state_clock_ms,
            server_clock_ms=server_now_ms,
        )
        raise HTTPException(status_code=400, detail={"error_code": "pick_clock_skew_rejected"})

    member = await _resolve_member(db, caller, group)

    set_valid = await _validate_set_in_event(db, payload.set_id, group.event_id, group.id)
    if not set_valid:
        raise HTTPException(status_code=404, detail={"error_code": "set_not_in_group_event"})

    # Fetch current state before upsert (to detect transitions)
    existing_result = await db.execute(
        select(Pick).where(Pick.member_id == member.id, Pick.set_id == payload.set_id)
    )
    existing = existing_result.scalar_one_or_none()
    prior_state: PickState | None = existing.state if existing else None  # type: ignore[assignment]

    stmt = (
        pg_insert(Pick)
        .values(
            member_id=member.id,
            set_id=payload.set_id,
            state=payload.state,
            state_clock_ms=payload.state_clock_ms,
        )
        .on_conflict_do_update(
            index_elements=["member_id", "set_id"],
            set_=dict(
                state=pg_insert(Pick).excluded.state,
                state_clock_ms=pg_insert(Pick).excluded.state_clock_ms,
                server_last_updated_at=datetime.now(timezone.utc),
            ),
            where=Pick.state_clock_ms < pg_insert(Pick).excluded.state_clock_ms,
        )
    )
    await db.execute(stmt)

    # Re-read to see who won — populate_existing bypasses identity-map cache
    row_result = await db.execute(
        select(Pick)
        .where(Pick.member_id == member.id, Pick.set_id == payload.set_id)
        .execution_options(populate_existing=True)
    )
    row = row_result.scalar_one()

    accepted = row.state_clock_ms == payload.state_clock_ms
    new_state: PickState = row.state  # type: ignore[assignment]

    if accepted and new_state != prior_state:
        kind = ActivityKind.pick_added if new_state == "active" else ActivityKind.pick_removed
        await log_activity(
            db,
            group_id=group.id,
            member_id=member.id,
            kind=kind,
            payload={"set_id": str(payload.set_id), "state": new_state},
        )

    group.last_active_at = datetime.now(timezone.utc)
    await db.flush()

    _logger.info(
        "pick.upserted",
        group_id=str(group.id),
        member_id=str(member.id),
        set_id=str(payload.set_id),
        state=new_state,
        state_clock_ms=row.state_clock_ms,
        accepted=accepted,
    )

    return PickResult(
        member_id=member.id,
        set_id=payload.set_id,
        state=new_state,
        state_clock_ms=row.state_clock_ms,
        accepted=accepted,
    )


async def upsert_picks_batch(
    db: AsyncSession,
    caller: User,
    group: Group,
    toggles: list[PickCreate],
) -> list[PickResult]:
    results: list[PickResult] = []
    for toggle in toggles:
        server_now_ms = _now_ms()
        if toggle.state_clock_ms > server_now_ms + _CLOCK_SKEW_BUFFER_MS:
            _logger.warning(
                "pick.clock_skew_rejected",
                group_id=str(group.id),
                set_id=str(toggle.set_id),
                incoming_clock_ms=toggle.state_clock_ms,
                server_clock_ms=server_now_ms,
            )
            results.append(
                PickResult(
                    member_id=caller.id,
                    set_id=toggle.set_id,
                    state=toggle.state,
                    state_clock_ms=toggle.state_clock_ms,
                    accepted=False,
                )
            )
            continue

        member_result = await db.execute(
            select(Member).where(Member.user_id == caller.id, Member.group_id == group.id)
        )
        member = member_result.scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=403, detail={"error_code": "not_a_member"})

        set_valid = await _validate_set_in_event(db, toggle.set_id, group.event_id, group.id)
        if not set_valid:
            results.append(
                PickResult(
                    member_id=member.id,
                    set_id=toggle.set_id,
                    state=toggle.state,
                    state_clock_ms=toggle.state_clock_ms,
                    accepted=False,
                )
            )
            continue

        existing_result = await db.execute(
            select(Pick).where(Pick.member_id == member.id, Pick.set_id == toggle.set_id)
        )
        existing = existing_result.scalar_one_or_none()
        prior_state: PickState | None = existing.state if existing else None  # type: ignore[assignment]

        stmt = (
            pg_insert(Pick)
            .values(
                member_id=member.id,
                set_id=toggle.set_id,
                state=toggle.state,
                state_clock_ms=toggle.state_clock_ms,
            )
            .on_conflict_do_update(
                index_elements=["member_id", "set_id"],
                set_=dict(
                    state=pg_insert(Pick).excluded.state,
                    state_clock_ms=pg_insert(Pick).excluded.state_clock_ms,
                    server_last_updated_at=datetime.now(timezone.utc),
                ),
                where=Pick.state_clock_ms < pg_insert(Pick).excluded.state_clock_ms,
            )
        )
        await db.execute(stmt)

        row_result = await db.execute(
            select(Pick)
            .where(Pick.member_id == member.id, Pick.set_id == toggle.set_id)
            .execution_options(populate_existing=True)
        )
        row = row_result.scalar_one()

        accepted = row.state_clock_ms == toggle.state_clock_ms
        new_state: PickState = row.state  # type: ignore[assignment]

        if accepted and new_state != prior_state:
            kind = ActivityKind.pick_added if new_state == "active" else ActivityKind.pick_removed
            await log_activity(
                db,
                group_id=group.id,
                member_id=member.id,
                kind=kind,
                payload={"set_id": str(toggle.set_id), "state": new_state},
            )

        results.append(
            PickResult(
                member_id=member.id,
                set_id=toggle.set_id,
                state=new_state,
                state_clock_ms=row.state_clock_ms,
                accepted=accepted,
            )
        )

    group.last_active_at = datetime.now(timezone.utc)
    await db.flush()

    return results
