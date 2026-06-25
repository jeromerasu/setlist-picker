from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.invite_code import generate_invite_code, normalize
from app.db.models.event import Event
from app.db.models.group import Group
from app.db.models.member import Member
from app.db.models.pick import Pick
from app.db.models.set_ import Set
from app.db.models.stage import Stage
from app.db.models.user import User
from app.db.uuid7 import uuid7
from app.schemas.groups import (
    EventSummary,
    GroupCreateResponse,
    GroupJoinResponse,
    GroupScheduleResponse,
    GroupSetItem,
    GroupStateResponse,
    MemberPickInfo,
    MyGroupListItem,
    MyGroupListResponse,
    PickSummary,
)
from app.services.activity_service import ActivityKind, log_activity
from app.services.member_service import resolve_member_out, resolve_member_out_batch

_logger = structlog.get_logger()

_MAX_INVITE_CODE_RETRIES = 5


async def _generate_unique_invite_code(db: AsyncSession) -> str:
    for attempt in range(1, _MAX_INVITE_CODE_RETRIES + 1):
        code = generate_invite_code()
        result = await db.execute(select(Group).where(Group.invite_code == code))
        if result.scalar_one_or_none() is None:
            return code
        _logger.info("group.invite_code_collision_retry", attempt=attempt)
    _logger.error("group.invite_code_collision_max_retries_exceeded")
    raise HTTPException(
        status_code=500,
        detail={"error_code": "invite_code_collision_unrecoverable"},
    )


async def create_group(
    db: AsyncSession,
    creator: User,
    name: str | None,
    event_id: uuid.UUID,
) -> GroupCreateResponse:
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        _logger.warning("group.event_not_found", event_id=str(event_id))
        raise HTTPException(status_code=404, detail={"error_code": "event_not_found"})

    invite_code = await _generate_unique_invite_code(db)
    resolved_name = name if name is not None else "Friends 🎵"

    now = datetime.now(timezone.utc)
    group = Group(
        id=uuid7(),
        name=resolved_name,
        invite_code=invite_code,
        event_id=event_id,
        created_by_user_id=creator.id,
        created_at=now,
        last_active_at=now,
    )

    try:
        async with db.begin_nested():
            db.add(group)
            await db.flush()

            member = Member(
                id=uuid7(),
                user_id=creator.id,
                group_id=group.id,
            )
            db.add(member)
            await db.flush()

            await log_activity(
                db,
                group_id=group.id,
                member_id=member.id,
                kind=ActivityKind.group_created,
                payload={
                    "group_name": group.name,
                    "event_id": str(event.event_id),
                    "event_name": event.name,
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("group.create_failed", event_id=str(event_id))
        raise HTTPException(status_code=500, detail={"error_code": "create_failed"}) from exc

    _logger.info(
        "group.created",
        group_id=str(group.id),
        invite_code=invite_code,
        event_id=str(event_id),
        created_by_user_id=str(creator.id),
    )

    return GroupCreateResponse(
        group_id=group.id,
        name=group.name,
        invite_code=invite_code,
        event_id=event_id,
        created_by_user_id=creator.id,
        created_at=now,
        member_id=member.id,
    )


async def join_group(
    db: AsyncSession,
    caller: User,
    raw_invite_code: str,
    display_name_override: str | None,
) -> tuple[GroupJoinResponse, bool]:
    """Returns (response, is_new_member). status 201 when is_new, 200 otherwise."""
    code = normalize(raw_invite_code.upper())

    result = await db.execute(select(Group).where(Group.invite_code == code))
    group = result.scalar_one_or_none()
    if group is None:
        _logger.warning("group.join_not_found", invite_code=code)
        raise HTTPException(status_code=404, detail={"error_code": "group_not_found"})

    # Check for existing membership (idempotent join)
    existing = await db.execute(
        select(Member).where(Member.user_id == caller.id, Member.group_id == group.id)
    )
    existing_member = existing.scalar_one_or_none()
    if existing_member is not None:
        member_out = resolve_member_out(existing_member, caller)
        group_item = MyGroupListItem(
            group_id=group.id,
            name=group.name,
            invite_code=group.invite_code,
            event_id=group.event_id,
            created_by_user_id=group.created_by_user_id,
            last_active_at=group.last_active_at,
            archived_at=group.archived_at,
            member_id=existing_member.id,
            joined_at=existing_member.joined_at,
        )
        return GroupJoinResponse(group=group_item, member=member_out, is_new_member=False), False

    # New member — use SAVEPOINT to handle concurrent join race
    member: Member | None = None
    try:
        async with db.begin_nested():
            member = Member(
                id=uuid7(),
                user_id=caller.id,
                group_id=group.id,
                display_name_override=display_name_override,
            )
            db.add(member)
            await db.flush()
    except Exception:
        # Concurrent join — re-select
        recheck = await db.execute(
            select(Member).where(Member.user_id == caller.id, Member.group_id == group.id)
        )
        member = recheck.scalar_one()

    assert member is not None

    await log_activity(
        db,
        group_id=group.id,
        member_id=member.id,
        kind=ActivityKind.member_joined,
        payload={"user_id": str(caller.id)},
    )

    # Bump last_active_at
    group.last_active_at = datetime.now(timezone.utc)
    await db.flush()

    _logger.info(
        "group.member_joined",
        group_id=str(group.id),
        user_id=str(caller.id),
        member_id=str(member.id),
    )

    member_out = resolve_member_out(member, caller)
    group_item = MyGroupListItem(
        group_id=group.id,
        name=group.name,
        invite_code=group.invite_code,
        event_id=group.event_id,
        created_by_user_id=group.created_by_user_id,
        last_active_at=group.last_active_at,
        archived_at=group.archived_at,
        member_id=member.id,
        joined_at=member.joined_at,
    )
    return GroupJoinResponse(group=group_item, member=member_out, is_new_member=True), True


async def list_my_groups(db: AsyncSession, caller: User) -> MyGroupListResponse:
    result = await db.execute(
        select(Group, Member)
        .join(Member, Member.group_id == Group.id)
        .where(Member.user_id == caller.id)
        .order_by(Group.last_active_at.desc())
    )
    rows = result.all()
    items = [
        MyGroupListItem(
            group_id=grp.id,
            name=grp.name,
            invite_code=grp.invite_code,
            event_id=grp.event_id,
            created_by_user_id=grp.created_by_user_id,
            last_active_at=grp.last_active_at,
            archived_at=grp.archived_at,
            member_id=mem.id,
            joined_at=mem.joined_at,
        )
        for grp, mem in rows
    ]
    return MyGroupListResponse(groups=items)


async def get_group_state(
    db: AsyncSession,
    caller: User,
    invite_code_raw: str,
) -> GroupStateResponse:
    code = normalize(invite_code_raw.upper())

    result = await db.execute(
        select(Group, Event)
        .join(Event, Event.event_id == Group.event_id)
        .where(Group.invite_code == code)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"error_code": "group_not_found"})

    group, event = row

    # Verify caller is a member
    mem_result = await db.execute(
        select(Member).where(Member.user_id == caller.id, Member.group_id == group.id)
    )
    if mem_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail={"error_code": "not_a_member"})

    # Load all members with their users
    members_result = await db.execute(
        select(Member, User)
        .join(User, User.id == Member.user_id)
        .where(Member.group_id == group.id)
    )
    member_rows = members_result.all()
    members_out = resolve_member_out_batch([(m, u) for m, u in member_rows])

    # Load all picks (active + tombstoned) sorted for deterministic FE diffing
    picks_result = await db.execute(
        select(Pick)
        .join(Member, Member.id == Pick.member_id)
        .where(Member.group_id == group.id)
        .order_by(Pick.member_id.asc(), Pick.set_id.asc())
    )
    picks = picks_result.scalars().all()
    picks_out = [
        PickSummary(
            member_id=p.member_id,
            set_id=p.set_id,
            state=p.state,
            state_clock_ms=p.state_clock_ms,
        )
        for p in picks
    ]
    _logger.debug(
        "group.state_picks_loaded",
        group_id=str(group.id),
        pick_count=len(picks_out),
    )

    event_out = EventSummary(
        event_id=event.event_id,
        name=event.name,
        start_date=event.start_date,
        end_date=event.end_date,
        location=event.location,
        timezone=event.timezone,
    )

    return GroupStateResponse(
        group_id=group.id,
        invite_code=group.invite_code,
        name=group.name,
        event=event_out,
        members=members_out,
        picks=picks_out,
        archived_at=group.archived_at,
        last_active_at=group.last_active_at,
    )


async def get_group_schedule(
    db: AsyncSession,
    caller: User,
    group: Group,
    day_label: str,
) -> GroupScheduleResponse:
    # Verify caller is a member of this group
    mem_result = await db.execute(
        select(Member).where(Member.user_id == caller.id, Member.group_id == group.id)
    )
    if mem_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail={"error_code": "not_a_member"})

    # Single round-trip: LEFT JOIN keeps zero-pick sets; COUNT FILTER in SQL.
    # Member JOIN filtered to this group so cross-group picks do not pollute counts.
    going_count_col = (
        func.count(Member.id)
        .filter(Pick.state == "active")
        .over(partition_by=Set.set_id)
        .label("going_count")
    )
    maybe_count_col = (
        func.count(Member.id)
        .filter(Pick.state == "maybe")
        .over(partition_by=Set.set_id)
        .label("maybe_count")
    )

    rows_result = await db.execute(
        select(
            Set.set_id,
            Set.display_name,
            Set.day_label,
            Set.starts_at,
            Set.ends_at,
            Stage.name.label("stage_name"),
            Stage.color_hex.label("stage_color_hex"),
            going_count_col,
            maybe_count_col,
            Pick.state.label("pick_state"),
            Member.id.label("member_id"),
            Member.display_name_override.label("member_display_name_override"),
            User.display_name.label("user_display_name"),
            User.avatar_color.label("user_avatar_color"),
        )
        .select_from(Set)
        .join(Stage, Stage.stage_id == Set.stage_id)
        .outerjoin(Pick, Pick.set_id == Set.set_id)
        .outerjoin(
            Member,
            and_(Member.id == Pick.member_id, Member.group_id == group.id),
        )
        .outerjoin(User, User.id == Member.user_id)
        .where(Set.event_id == group.event_id, Set.day_label == day_label)
        .order_by(Set.starts_at.asc(), Member.joined_at.asc())
    )
    rows = rows_result.all()

    # Aggregate going_members in Python; going_count/maybe_count come from SQL
    sets_seen: dict[uuid.UUID, GroupSetItem] = {}
    for row in rows:
        set_id: uuid.UUID = row.set_id
        if set_id not in sets_seen:
            sets_seen[set_id] = GroupSetItem(
                set_id=set_id,
                display_name=row.display_name,
                stage_name=row.stage_name,
                stage_color_hex=row.stage_color_hex,
                day_label=row.day_label,
                starts_at=row.starts_at,
                ends_at=row.ends_at,
                going_count=row.going_count,
                maybe_count=row.maybe_count,
                going_members=[],
            )
        if row.member_id is not None and row.pick_state == "active":
            display_name = row.member_display_name_override or row.user_display_name or "Member"
            sets_seen[set_id].going_members.append(
                MemberPickInfo(
                    member_id=row.member_id,
                    display_name=display_name,
                    avatar_color=row.user_avatar_color,
                )
            )

    sets_out = list(sets_seen.values())

    _logger.info(
        "group.schedule.computed",
        entity_id=group.invite_code,
        day_label=day_label,
        set_count=len(sets_out),
        statement_count=1,
    )

    return GroupScheduleResponse(
        group_id=group.id,
        event_id=group.event_id,
        day_label=day_label,
        sets=sets_out,
    )
