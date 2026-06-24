from __future__ import annotations

import structlog

from app.db.models.member import Member
from app.db.models.user import User
from app.schemas.groups import MemberOut

_logger = structlog.get_logger()


def _resolve_display_name(member: Member, user: User) -> str:
    if member.display_name_override:
        return member.display_name_override
    if user.display_name:
        return user.display_name
    _logger.warning("member.display_name_fallback", member_id=str(member.id))
    return "Member"


def resolve_member_out(member: Member, user: User) -> MemberOut:
    return MemberOut(
        member_id=member.id,
        user_id=user.id,
        group_id=member.group_id,
        display_name=_resolve_display_name(member, user),
        display_name_override=member.display_name_override,
        avatar_color=user.avatar_color,
        joined_at=member.joined_at,
    )


def resolve_member_out_batch(rows: list[tuple[Member, User]]) -> list[MemberOut]:
    return [resolve_member_out(m, u) for m, u in rows]
