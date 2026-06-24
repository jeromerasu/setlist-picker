from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import structlog
from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist, SetArtist
from app.db.models.event import Event
from app.db.models.group import Group
from app.db.models.member import Member
from app.db.models.pick import Pick
from app.db.models.set_ import Set
from app.db.models.stage import Stage
from app.db.models.user import User
from app.schemas.snapshot import (
    GroupSnapshotResponse,
    SnapshotMember,
    SnapshotSet,
    SnapshotStage,
)


@dataclass
class _SetAcc:
    set_id: uuid.UUID
    display_name: str
    artist_names: list[str]
    day_label: str
    starts_at: datetime
    ends_at: datetime
    pickers: list[SnapshotMember] = field(default_factory=list)


@dataclass
class _StageAcc:
    stage_id: uuid.UUID
    name: str
    display_order: int
    set_ids: list[uuid.UUID] = field(default_factory=list)


_logger = structlog.get_logger()


async def get_snapshot(
    db: AsyncSession,
    caller: User,
    group: Group,
    at: datetime,
    window_minutes: int,
) -> GroupSnapshotResponse:
    # Verify caller is a member
    member_result = await db.execute(
        select(Member).where(Member.group_id == group.id, Member.user_id == caller.id)
    )
    if member_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail={"error_code": "not_a_member"})

    # Fetch event
    event_result = await db.execute(select(Event).where(Event.event_id == group.event_id))
    event = event_result.scalar_one()

    # Count all members in the group
    count_result = await db.execute(select(func.count()).where(Member.group_id == group.id))
    members_total: int = count_result.scalar_one() or 0

    # Q2: sets overlapping [at, at + window_minutes] with stage + active picks + member + user
    window_end = at + timedelta(minutes=window_minutes)
    q2 = (
        select(
            Set.set_id,
            Set.stage_id,
            Set.display_name.label("set_display_name"),
            Set.day_label,
            Set.starts_at,
            Set.ends_at,
            Stage.name.label("stage_name"),
            Stage.display_order,
            Pick.member_id,
            Member.user_id,
            func.coalesce(
                Member.display_name_override,
                User.display_name,
            ).label("member_display_name"),
            User.avatar_color,
        )
        .where(
            Set.event_id == group.event_id,
            Set.starts_at < window_end,
            Set.ends_at > at,
        )
        .join(Stage, Stage.stage_id == Set.stage_id)
        .outerjoin(
            Pick,
            and_(Pick.set_id == Set.set_id, Pick.state == "active"),
        )
        .outerjoin(
            Member,
            and_(Member.id == Pick.member_id, Member.group_id == group.id),
        )
        .outerjoin(User, User.id == Member.user_id)
        .order_by(Stage.display_order.asc(), Set.starts_at.asc())
    )
    q2_result = await db.execute(q2)
    rows = q2_result.all()

    # Collect set_ids for artist query
    set_ids_in_window: list[uuid.UUID] = list(dict.fromkeys(row.set_id for row in rows))

    # Artist names per set (position-ordered)
    artist_names_by_set: dict[uuid.UUID, list[str]] = {}
    if set_ids_in_window:
        artist_q = (
            select(SetArtist.set_id, Artist.name)
            .join(Artist, Artist.artist_id == SetArtist.artist_id)
            .where(SetArtist.set_id.in_(set_ids_in_window))
            .order_by(SetArtist.set_id, SetArtist.position.asc())
        )
        artist_result = await db.execute(artist_q)
        for ar in artist_result.all():
            artist_names_by_set.setdefault(ar.set_id, []).append(ar.name)

    # Build hierarchical response from ordered Q2 rows
    stage_order: list[uuid.UUID] = []
    stages: dict[uuid.UUID, _StageAcc] = {}
    sets: dict[uuid.UUID, _SetAcc] = {}

    for row in rows:
        stage_id: uuid.UUID = row.stage_id
        set_id: uuid.UUID = row.set_id

        if stage_id not in stages:
            stage_order.append(stage_id)
            stages[stage_id] = _StageAcc(
                stage_id=stage_id,
                name=str(row.stage_name),
                display_order=int(row.display_order),
            )

        if set_id not in sets:
            stages[stage_id].set_ids.append(set_id)
            sets[set_id] = _SetAcc(
                set_id=set_id,
                display_name=str(row.set_display_name),
                artist_names=artist_names_by_set.get(set_id, []),
                day_label=str(row.day_label),
                starts_at=row.starts_at,
                ends_at=row.ends_at,
            )

        if row.member_id is not None:
            sets[set_id].pickers.append(
                SnapshotMember(
                    user_id=row.user_id,
                    member_id=row.member_id,
                    display_name=(
                        str(row.member_display_name) if row.member_display_name else "Member"
                    ),
                    avatar_color=str(row.avatar_color),
                )
            )

    stage_list = [
        SnapshotStage(
            stage_id=stages[sid].stage_id,
            name=stages[sid].name,
            display_order=stages[sid].display_order,
            sets=[
                SnapshotSet(
                    set_id=sets[sid2].set_id,
                    display_name=sets[sid2].display_name,
                    artist_names=sets[sid2].artist_names,
                    day_label=sets[sid2].day_label,
                    starts_at=sets[sid2].starts_at,
                    ends_at=sets[sid2].ends_at,
                    pickers=sets[sid2].pickers,
                )
                for sid2 in stages[sid].set_ids
            ],
        )
        for sid in stage_order
    ]

    _logger.debug(
        "snapshot.served",
        group_id=str(group.id),
        at=at.isoformat(),
        window_minutes=window_minutes,
        set_count=len(sets),
        picker_count=sum(len(s.pickers) for s in sets.values()),
        members_total=members_total,
    )

    return GroupSnapshotResponse(
        group_id=group.id,
        invite_code=group.invite_code,
        group_name=group.name,
        event_id=event.event_id,
        event_name=event.name,
        timezone=event.timezone,
        snapshot_at=at,
        window_minutes=window_minutes,
        members_total=members_total,
        stages=stage_list,
    )
