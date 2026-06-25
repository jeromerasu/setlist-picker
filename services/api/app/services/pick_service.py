from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

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
    """Batch sync — single INSERT ON CONFLICT against pick table (1 statement total).

    Within-batch LWW: duplicate set_ids are deduplicated by highest state_clock_ms
    before the INSERT so PostgreSQL never sees two VALUES rows for the same key.
    """
    server_now_ms = _now_ms()

    # 1. Resolve member once (1 query, member table)
    member_result = await db.execute(
        select(Member).where(Member.user_id == caller.id, Member.group_id == group.id)
    )
    member = member_result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=403, detail={"error_code": "not_a_member"})

    # 2. Filter clock-skew rejects in Python — no DB query
    valid_toggles: list[PickCreate] = []
    results: list[PickResult] = []
    for toggle in toggles:
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
                    member_id=member.id,
                    set_id=toggle.set_id,
                    state=toggle.state,
                    state_clock_ms=toggle.state_clock_ms,
                    accepted=False,
                )
            )
        else:
            valid_toggles.append(toggle)

    if not valid_toggles:
        group.last_active_at = datetime.now(timezone.utc)
        await db.flush()
        _logger.info(
            "group.picks.sync",
            entity_id=str(member.id),
            batch_size=len(toggles),
            statement_count=0,
        )
        return results

    # 3. Validate all set_ids in bulk (1 query, set table)
    incoming_set_ids = list({t.set_id for t in valid_toggles})
    valid_sets_result = await db.execute(
        select(Set.set_id).where(
            Set.set_id.in_(incoming_set_ids), Set.event_id == group.event_id
        )
    )
    valid_set_ids: set[uuid.UUID] = {row[0] for row in valid_sets_result.all()}

    upsert_toggles: list[PickCreate] = []
    for toggle in valid_toggles:
        if toggle.set_id not in valid_set_ids:
            _logger.warning(
                "pick.set_id_not_in_event",
                group_id=str(group.id),
                set_id=str(toggle.set_id),
            )
            results.append(
                PickResult(
                    member_id=member.id,
                    set_id=toggle.set_id,
                    state=toggle.state,
                    state_clock_ms=toggle.state_clock_ms,
                    accepted=False,
                )
            )
        else:
            upsert_toggles.append(toggle)

    if not upsert_toggles:
        group.last_active_at = datetime.now(timezone.utc)
        await db.flush()
        _logger.info(
            "group.picks.sync",
            entity_id=str(member.id),
            batch_size=len(toggles),
            statement_count=0,
        )
        return results

    # 4. Within-batch LWW dedup: keep highest clock per set_id
    # PostgreSQL raises if two VALUES rows share the same unique-constraint key.
    deduped: dict[uuid.UUID, PickCreate] = {}
    for toggle in upsert_toggles:
        existing = deduped.get(toggle.set_id)
        if existing is None or toggle.state_clock_ms > existing.state_clock_ms:
            deduped[toggle.set_id] = toggle

    # 5. Single batch UPSERT — LWW semantics preserved verbatim (1 statement, pick table)
    now_utc = datetime.now(timezone.utc)
    base_stmt = pg_insert(Pick).values(
        [
            {
                "member_id": member.id,
                "set_id": t.set_id,
                "state": t.state,
                "state_clock_ms": t.state_clock_ms,
            }
            for t in deduped.values()
        ]
    )
    upsert_stmt: Any = base_stmt.on_conflict_do_update(
        index_elements=["member_id", "set_id"],
        set_={
            "state": base_stmt.excluded.state,
            "state_clock_ms": base_stmt.excluded.state_clock_ms,
            "server_last_updated_at": now_utc,
        },
        where=Pick.state_clock_ms < base_stmt.excluded.state_clock_ms,
    ).returning(
        Pick.member_id, Pick.set_id, Pick.state, Pick.state_clock_ms
    )

    cursor: Any = await db.execute(upsert_stmt)
    # RETURNING only includes rows that were inserted or DO UPDATE-ed (WHERE true).
    # Stale rows (WHERE false) are absent — those get accepted=False below.
    returned_map: dict[uuid.UUID, Any] = {row.set_id: row for row in cursor.fetchall()}

    # 6. Build result list in input order; handle within-batch superseded duplicates
    for toggle in upsert_toggles:
        winning = deduped.get(toggle.set_id)
        if winning is not None and winning.state_clock_ms != toggle.state_clock_ms:
            # Lower-clock duplicate within this batch — superseded by winning entry
            results.append(
                PickResult(
                    member_id=member.id,
                    set_id=toggle.set_id,
                    state=toggle.state,
                    state_clock_ms=toggle.state_clock_ms,
                    accepted=False,
                )
            )
        else:
            returned = returned_map.get(toggle.set_id)
            if returned is not None:
                results.append(
                    PickResult(
                        member_id=member.id,
                        set_id=toggle.set_id,
                        state=returned.state,
                        state_clock_ms=returned.state_clock_ms,
                        accepted=returned.state_clock_ms == toggle.state_clock_ms,
                    )
                )
            else:
                # DB had a higher clock (WHERE false) — not in RETURNING
                results.append(
                    PickResult(
                        member_id=member.id,
                        set_id=toggle.set_id,
                        state=toggle.state,
                        state_clock_ms=toggle.state_clock_ms,
                        accepted=False,
                    )
                )

    group.last_active_at = datetime.now(timezone.utc)
    await db.flush()

    _logger.info(
        "group.picks.sync",
        entity_id=str(member.id),
        batch_size=len(toggles),
        statement_count=1,
    )

    return results
