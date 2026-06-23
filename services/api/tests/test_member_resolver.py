"""BE-010: resolve_member_out / resolve_member_out_batch unit tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.db.models.member import Member
from app.db.models.user import User
from app.services.member_service import resolve_member_out, resolve_member_out_batch


def _make_user(
    username: str | None = "testuser",
    display_name: str | None = None,
    avatar_color: str = "#AABBCC",
) -> User:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.username = username
    u.display_name = display_name
    u.avatar_color = avatar_color
    return u


def _make_member(
    user_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
    display_name_override: str | None = None,
) -> Member:
    m = MagicMock(spec=Member)
    m.id = uuid.uuid4()
    m.user_id = user_id or uuid.uuid4()
    m.group_id = group_id or uuid.uuid4()
    m.display_name_override = display_name_override
    m.joined_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    return m


def test_display_name_override_takes_priority() -> None:
    user = _make_user(username="user1", display_name="Real Name")
    member = _make_member(display_name_override="DJ Override")
    out = resolve_member_out(member, user)
    assert out.display_name == "DJ Override"


def test_display_name_falls_back_to_user_display_name() -> None:
    user = _make_user(username="user2", display_name="Real Name")
    member = _make_member(display_name_override=None)
    out = resolve_member_out(member, user)
    assert out.display_name == "Real Name"


def test_display_name_falls_back_to_username() -> None:
    user = _make_user(username="user3", display_name=None)
    member = _make_member(display_name_override=None)
    out = resolve_member_out(member, user)
    assert out.display_name == "user3"


def test_display_name_falls_back_to_member_literal() -> None:
    user = _make_user(username=None, display_name=None)
    member = _make_member(display_name_override=None)
    out = resolve_member_out(member, user)
    assert out.display_name == "Member"


def test_avatar_color_from_user() -> None:
    user = _make_user(avatar_color="#112233")
    member = _make_member()
    out = resolve_member_out(member, user)
    assert out.avatar_color == "#112233"


def test_ids_mapped_correctly() -> None:
    user = _make_user()
    member = _make_member(user_id=user.id)
    out = resolve_member_out(member, user)
    assert out.member_id == member.id
    assert out.user_id == user.id
    assert out.group_id == member.group_id


def test_display_name_override_in_out() -> None:
    user = _make_user()
    member = _make_member(display_name_override="DJ Name")
    out = resolve_member_out(member, user)
    assert out.display_name_override == "DJ Name"


def test_resolve_member_out_batch_returns_list() -> None:
    user1 = _make_user(username="u1")
    user2 = _make_user(username="u2")
    m1 = _make_member(user_id=user1.id)
    m2 = _make_member(user_id=user2.id)
    results = resolve_member_out_batch([(m1, user1), (m2, user2)])
    assert len(results) == 2
    assert {r.display_name for r in results} == {"u1", "u2"}
