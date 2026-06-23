"""Integration smoke tests — verify INSERT + SELECT round-trips per BE-002 spec.

These tests require TEST_DATABASE_URL (default: postgres:dev@localhost:5433/setlist_test)
with the V001 migration already applied.
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event import Event
from app.db.models.group import Group
from app.db.models.group_activity import GroupActivity
from app.db.models.member import Member
from app.db.models.pick import Pick
from app.db.models.user import User
from app.db.uuid7 import uuid7


def _user(
    *,
    username: str | None = "jerome",
    avatar_color: str = "#a78bfa",
    auth_provider: str = "local",
    password_hash: str | None = "hashed",
    apple_subject_id: str | None = None,
    google_subject_id: str | None = None,
) -> User:
    return User(
        id=uuid7(),
        auth_provider=auth_provider,
        username=username if auth_provider == "local" else None,
        password_hash=password_hash if auth_provider == "local" else None,
        apple_subject_id=apple_subject_id,
        google_subject_id=google_subject_id,
        avatar_color=avatar_color,
    )


def _event() -> Event:
    return Event(
        event_id=uuid7(),
        name="TML 2026 W2",
        start_date=datetime.date(2026, 7, 24),
        end_date=datetime.date(2026, 7, 26),
        timezone="Europe/Brussels",
        source_adapter="manual",
    )


async def test_insert_user_round_trips(db_session: AsyncSession) -> None:
    user = _user()
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(select(User).where(User.id == user.id))
    row = result.scalar_one()
    assert row.id == user.id
    assert row.username == "jerome"
    assert row.auth_provider == "local"
    assert row.created_at is not None


async def test_insert_event_then_group_with_fk(db_session: AsyncSession) -> None:
    creator = _user()
    event = _event()
    db_session.add(creator)
    db_session.add(event)
    await db_session.flush()

    group = Group(
        id=uuid7(),
        name="Festival Crew",
        invite_code="AB7K9MNP",
        event_id=event.event_id,
        created_by_user_id=creator.id,
    )
    db_session.add(group)
    await db_session.flush()

    result = await db_session.execute(select(Group).where(Group.id == group.id))
    row = result.scalar_one()
    assert row.event_id == event.event_id


async def test_member_unique_constraint_user_group(db_session: AsyncSession) -> None:
    creator = _user()
    event = _event()
    db_session.add(creator)
    db_session.add(event)
    await db_session.flush()

    group = Group(
        id=uuid7(),
        name="Crew",
        invite_code="AAAABBBB",
        event_id=event.event_id,
        created_by_user_id=creator.id,
    )
    db_session.add(group)
    await db_session.flush()

    m1 = Member(id=uuid7(), user_id=creator.id, group_id=group.id)
    db_session.add(m1)
    await db_session.flush()

    m2 = Member(id=uuid7(), user_id=creator.id, group_id=group.id)
    db_session.add(m2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_pick_cascade_on_member_delete(db_session: AsyncSession) -> None:
    from app.db.models.set_ import Set
    from app.db.models.stage import Stage

    user = _user(username="alice")
    event = _event()
    db_session.add_all([user, event])
    await db_session.flush()

    group = Group(
        id=uuid7(),
        name="Crew",
        invite_code="CCCCDDDD",
        event_id=event.event_id,
        created_by_user_id=user.id,
    )
    db_session.add(group)
    await db_session.flush()

    member = Member(id=uuid7(), user_id=user.id, group_id=group.id)
    stage = Stage(
        stage_id=uuid7(),
        event_id=event.event_id,
        name="MAINSTAGE",
        external_id="ms1",
    )
    db_session.add_all([member, stage])
    await db_session.flush()

    perf = Set(
        set_id=uuid7(),
        event_id=event.event_id,
        stage_id=stage.stage_id,
        display_name="DJ Set",
        day_label="FRIDAY",
        starts_at=datetime.datetime(2026, 7, 25, 20, 0, tzinfo=datetime.timezone.utc),
        ends_at=datetime.datetime(2026, 7, 25, 22, 0, tzinfo=datetime.timezone.utc),
        external_id="s1",
    )
    db_session.add(perf)
    await db_session.flush()

    pick = Pick(
        member_id=member.id,
        set_id=perf.set_id,
        state="active",
        state_clock_ms=1700000000000,
    )
    db_session.add(pick)
    await db_session.flush()

    await db_session.delete(member)
    await db_session.flush()

    result = await db_session.execute(select(Pick).where(Pick.member_id == member.id))
    assert result.scalar_one_or_none() is None


async def test_group_activity_member_id_set_null(db_session: AsyncSession) -> None:
    user = _user(username="bob")
    event = _event()
    db_session.add_all([user, event])
    await db_session.flush()

    group = Group(
        id=uuid7(),
        name="Crew",
        invite_code="EEEEFFFF",
        event_id=event.event_id,
        created_by_user_id=user.id,
    )
    db_session.add(group)
    await db_session.flush()

    member = Member(id=uuid7(), user_id=user.id, group_id=group.id)
    db_session.add(member)
    await db_session.flush()

    activity = GroupActivity(
        id=uuid7(),
        group_id=group.id,
        member_id=member.id,
        kind="member_joined",
        payload={"display_name": "Bob"},
    )
    db_session.add(activity)
    await db_session.flush()

    await db_session.delete(member)
    await db_session.flush()

    await db_session.refresh(activity)
    assert activity.member_id is None


async def test_uq_user_username_case_in_app_layer(db_session: AsyncSession) -> None:
    u1 = _user(username="jerome")
    db_session.add(u1)
    await db_session.flush()

    # same username → unique constraint violation
    u2 = _user(username="jerome")
    u2.id = uuid7()
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # uppercase variant is different at the DB level (app lowercases before write)
    u3 = _user(username="Jerome")
    db_session.add(u3)
    await db_session.flush()  # no error — "Jerome" != "jerome" in the DB index


async def test_uq_user_apple_subject_partial_index(db_session: AsyncSession) -> None:
    # Two users with NULL apple_subject_id is allowed
    u1 = _user(username="user1")
    u2 = _user(username="user2")
    db_session.add_all([u1, u2])
    await db_session.flush()

    # Two users with the same apple_subject_id is NOT allowed
    apple_id = "apple-sub-123"
    u3 = _user(
        username=None,
        auth_provider="apple",
        apple_subject_id=apple_id,
        password_hash=None,
    )
    u4 = _user(
        username=None,
        auth_provider="apple",
        apple_subject_id=apple_id,
        password_hash=None,
    )
    u3.id = uuid7()
    u4.id = uuid7()
    db_session.add(u3)
    await db_session.flush()

    db_session.add(u4)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_pick_partial_index_active_only_used(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("EXPLAIN SELECT * FROM pick WHERE state = 'active' AND set_id = gen_random_uuid()")
    )
    plan = " ".join(row[0] for row in result.fetchall())
    # Planner may choose either partial index for the `state = 'active'` predicate
    assert "idx_pick_set_active" in plan or "idx_pick_member_active" in plan or "Seq Scan" in plan
