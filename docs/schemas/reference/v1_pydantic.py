"""
v1 Pydantic reference shapes — companion to ADR-006.

THIS FILE IS A DESIGN ARTIFACT. It is intentionally NOT imported anywhere in
services/api/. The Phase 1 implementer reads this file and copies / adapts
these shapes into the actual FastAPI Pydantic models. Until then, this file is
the canonical wire-shape reference.

Conventions (per CLAUDE.md and ADR-006):

- snake_case field names everywhere (Pydantic v2 default).
- TZ-aware datetimes on the wire as ISO-8601 with offset.
- Pick state_clock_ms is the client-assigned Unix epoch ms; see ADR-006 § 4.5.
- Username + email are stored lowercased; the server lowercases on every write.
- Auth: JWT (HS256), 24h access + 7d refresh. Every endpoint except
  /auth/{signup,login,refresh} requires Authorization: Bearer <access_token>.
- Group-scoped endpoints additionally require the caller to be an active Member
  of the group identified by the path's invite_code; the server derives
  member_id from (current_user.id, group.id) — clients do NOT send member_id.

Mypy-strict-clean and ruff-clean as written.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class _Model(BaseModel):
    """Project base: forbid unknown fields on input, populate cleanly on output."""

    model_config = ConfigDict(extra="forbid", frozen=False)


class PickState(str, Enum):
    """Mirror of pick.state. Stored as string per ADR-006 § 2.10."""

    active = "active"
    tombstoned = "tombstoned"


class SimilaritySource(str, Enum):
    """Mirror of artist_cache.similarity_source per ADR-005."""

    spotify_v2 = "spotify_v2"
    lastfm = "lastfm"
    genre_overlap = "genre_overlap"
    none = "none"


class CacheStatus(str, Enum):
    """Per artist-drilldown-spec API contract."""

    fresh = "fresh"
    stale = "stale"
    miss = "miss"


class TokenType(str, Enum):
    access = "access"
    refresh = "refresh"


class SocialLinks(_Model):
    """Loose-shape artist social links from the lineup adapter."""

    spotify: str | None = None
    instagram: str | None = None
    soundcloud: str | None = None
    tiktok: str | None = None
    twitter: str | None = None
    facebook: str | None = None
    youtube: str | None = None
    website: str | None = None


# ---------------------------------------------------------------------------
# Auth — POST /api/auth/signup, /login, /refresh
# ---------------------------------------------------------------------------
# Username + password + optional email. JWT pair returned. ADR-006 § 1 + § 4.16,
# 4.17, 4.18, 4.19.


class UserCreate(_Model):
    """Signup payload. The server lowercases username/email before storing."""

    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=80)


class UserLogin(_Model):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class UserOut(_Model):
    """Public-facing user shape returned by auth and /users/me endpoints."""

    id: UUID
    username: str  # always lowercase on the wire
    email: EmailStr | None
    display_name: str | None
    avatar_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    created_at: datetime
    last_login_at: datetime | None


class UserUpdate(_Model):
    """PATCH /api/users/me — partial update."""

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    avatar_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    # Password change is intentionally a separate endpoint (out of scope here).


class TokenPair(_Model):
    """JWT pair returned by signup / login / refresh.

    access_token: 24h. refresh_token: 7d.
    Both signed HS256 with JWT_SECRET. Claims: sub (user.id), iat, exp, type.
    Refresh token also carries jti for v2 revocation (not used in v1).
    """

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime


class AuthResponse(_Model):
    """Wrapper returned by /auth/signup and /auth/login."""

    user: UserOut
    tokens: TokenPair


class TokenRefreshRequest(_Model):
    refresh_token: str


# ---------------------------------------------------------------------------
# GET /api/users/me — current user
# ---------------------------------------------------------------------------
# Response: UserOut (defined above).


# ---------------------------------------------------------------------------
# GET /api/users/me/groups — the authenticated user's groups
# ---------------------------------------------------------------------------


class MyGroupListItem(_Model):
    group_id: UUID
    name: str
    invite_code: str = Field(min_length=8, max_length=8)
    event_id: UUID
    created_by_user_id: UUID
    last_active_at: datetime
    archived_at: datetime | None
    member_id: UUID  # the caller's Member row in this group
    joined_at: datetime


class MyGroupListResponse(_Model):
    groups: list[MyGroupListItem]


# ---------------------------------------------------------------------------
# POST /api/groups — create a group
# ---------------------------------------------------------------------------


class GroupCreate(_Model):
    """Authenticated user creates a group. The creator auto-becomes a Member."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    event_id: UUID


class GroupCreateResponse(_Model):
    group_id: UUID
    name: str
    invite_code: str = Field(min_length=8, max_length=8)
    event_id: UUID
    created_by_user_id: UUID
    created_at: datetime
    member_id: UUID  # the creator's Member row


# ---------------------------------------------------------------------------
# POST /api/groups/join — join via invite code
# ---------------------------------------------------------------------------


class GroupJoinRequest(_Model):
    invite_code: str = Field(min_length=8, max_length=8)
    display_name_override: str | None = Field(default=None, min_length=1, max_length=80)


class MemberOut(_Model):
    """Per-group membership identity. Used in join responses and group state."""

    member_id: UUID
    user_id: UUID
    group_id: UUID
    display_name: str  # resolved: override → user.display_name → user.username
    display_name_override: str | None
    avatar_color: str
    joined_at: datetime
    left_at: datetime | None


class GroupJoinResponse(_Model):
    group: MyGroupListItem
    member: MemberOut
    is_new_member: bool  # False if the user was already a Member (rejoin re-activates).


# ---------------------------------------------------------------------------
# POST /api/groups/{invite_code}/leave — soft-remove the calling user
# ---------------------------------------------------------------------------
# No request body (current_user + path identifies the Member).


class GroupLeaveResponse(_Model):
    member_id: UUID
    left_at: datetime


# ---------------------------------------------------------------------------
# GET /api/groups/{invite_code} — group state (members + picks)
# ---------------------------------------------------------------------------
# Polled every 15s per ADR-006 § 4.14. Supports If-Modified-Since → 304.


class PickSummary(_Model):
    """Tombstoned picks ARE included so the FE can reconcile its IndexedDB queue."""

    member_id: UUID
    set_id: UUID
    state: PickState
    state_clock_ms: int = Field(ge=0)


class EventSummary(_Model):
    event_id: UUID
    name: str
    start_date: date
    end_date: date
    location: str | None
    timezone: str  # IANA, e.g. "Europe/Brussels"


class GroupStateResponse(_Model):
    group_id: UUID
    invite_code: str
    name: str
    event: EventSummary
    members: list[MemberOut]
    picks: list[PickSummary]
    archived_at: datetime | None
    last_active_at: datetime


# ---------------------------------------------------------------------------
# PATCH /api/groups/{invite_code} — rename
# ---------------------------------------------------------------------------


class GroupRenameRequest(_Model):
    name: str = Field(min_length=1, max_length=80)


class GroupRenameResponse(_Model):
    group_id: UUID
    invite_code: str
    name: str


# ---------------------------------------------------------------------------
# POST /api/groups/{invite_code}/picks — add or upsert a pick
# ---------------------------------------------------------------------------
# member_id is NOT in the request — the server derives it from (current_user,
# group). Prevents picks-on-behalf-of-another-member.


class PickCreate(_Model):
    set_id: UUID
    state: PickState
    state_clock_ms: int = Field(ge=0)


class PickResult(_Model):
    """Server-final state after LWW resolution (ADR-006 § 4.5)."""

    member_id: UUID
    set_id: UUID
    state: PickState
    state_clock_ms: int
    accepted: bool  # False if the incoming clock lost the LWW comparison.


# ---------------------------------------------------------------------------
# POST /api/groups/{invite_code}/picks/sync — bulk drain of the offline queue
# ---------------------------------------------------------------------------


class PickSyncRequest(_Model):
    toggles: list[PickCreate]


class PickSyncResponse(_Model):
    results: list[PickResult]


# ---------------------------------------------------------------------------
# DELETE /api/groups/{invite_code}/picks/{set_id} — explicit unpick
# ---------------------------------------------------------------------------


class PickRemoveRequest(_Model):
    state_clock_ms: int = Field(ge=0)


# ---------------------------------------------------------------------------
# GET /api/events — list events available on this deploy
# ---------------------------------------------------------------------------


class EventListItem(_Model):
    event_id: UUID
    name: str
    start_date: date
    end_date: date
    location: str | None
    timezone: str


class EventListResponse(_Model):
    events: list[EventListItem]


# ---------------------------------------------------------------------------
# GET /api/events/{event_id}/lineup — stages + sets + artists for an event
# ---------------------------------------------------------------------------


class StageDetail(_Model):
    stage_id: UUID
    name: str
    display_order: int
    external_id: str


class ArtistRef(_Model):
    artist_id: UUID
    name: str
    position: int = Field(ge=0)
    image_url: str | None = None
    social_links: SocialLinks | None = None


class SetDetail(_Model):
    set_id: UUID
    stage_id: UUID
    display_name: str
    day_label: str  # FRIDAY / SATURDAY / SUNDAY
    starts_at: datetime
    ends_at: datetime
    external_id: str
    artists: list[ArtistRef]


class EventLineupResponse(_Model):
    event: EventSummary
    stages: list[StageDetail]
    sets: list[SetDetail]


# ---------------------------------------------------------------------------
# POST /api/events/import — admin paste-import of a lineup JSON payload
# ---------------------------------------------------------------------------


class LineupSourceArtist(_Model):
    """Mirrors the source JSON artist shape (verified against tml26-w2.json)."""

    id: str
    name: str
    image: str | None = None
    spotify: str | None = None
    instagram: str | None = None
    soundcloud: str | None = None
    tiktok: str | None = None
    twitter: str | None = None
    facebook: str | None = None
    youtube: str | None = None
    website: str | None = None


class LineupSourceStage(_Model):
    id: str
    name: str


class LineupSourcePerformance(_Model):
    id: str
    name: str
    artists: list[LineupSourceArtist] = Field(min_length=1)
    stage: LineupSourceStage
    date: date
    day: str
    startTime: str  # source-formatted as 'YYYY-MM-DD HH:MM:SS+HH:MM'
    endTime: str


class LineupImportRequest(_Model):
    event_name: str
    start_date: date
    end_date: date
    timezone: str
    location: str | None = None
    source_adapter: Literal["event_api_v1", "manual"]
    external_id: str | None = None
    performances: list[LineupSourcePerformance]


class LineupImportResponse(_Model):
    event_id: UUID
    stages_created: int
    stages_updated: int
    sets_created: int
    sets_updated: int
    artists_created: int
    artists_linked: int
    imported_at: datetime


# ---------------------------------------------------------------------------
# GET /api/groups/{invite_code}/snapshot — screenshotable view (ADR-006 § 4.13)
# ---------------------------------------------------------------------------
# All-member visibility. Designed for self-contained screen captures: every
# label the recipient might lack (event name, stage names, times, picker names)
# is on the same payload. Display names resolved server-side via
# COALESCE(member.display_name_override, user.display_name, user.username).


class SnapshotMember(_Model):
    user_id: UUID
    member_id: UUID
    display_name: str
    avatar_color: str


class SnapshotSet(_Model):
    set_id: UUID
    display_name: str
    artist_names: list[str] = Field(min_length=1)
    day_label: str
    starts_at: datetime
    ends_at: datetime
    pickers: list[SnapshotMember]  # active picks only; all members' picks (not just caller).


class SnapshotStage(_Model):
    stage_id: UUID
    name: str
    display_order: int
    sets: list[SnapshotSet]


class GroupSnapshotResponse(_Model):
    group_id: UUID
    invite_code: str
    group_name: str
    event_id: UUID
    event_name: str
    timezone: str  # IANA
    snapshot_at: datetime
    window_minutes: int
    members_total: int  # "5 of 8 friends going" headline
    stages: list[SnapshotStage]


# ---------------------------------------------------------------------------
# GET /api/artists/{artist_name} — artist drill-down
# ---------------------------------------------------------------------------


class SimilarArtist(_Model):
    name: str
    similarity_source: SimilaritySource


class TopTrack(_Model):
    name: str
    preview_url: str | None
    spotify_url: str | None
    image_url: str | None


class ArtistDetailResponse(_Model):
    artist_name: str
    spotify_artist_id: str | None
    image_url: str | None
    genres: list[str]
    similar_artists: list[SimilarArtist]
    top_track: TopTrack | None
    cache_status: CacheStatus
    fetched_at: datetime | None


# ---------------------------------------------------------------------------
# Error shape — used by FastAPI exception handlers
# ---------------------------------------------------------------------------


class ErrorResponse(_Model):
    """Standardized error body. CLAUDE.md NF-002 requires the top-level handler
    log full tracebacks via logger.exception(...); the wire body is the summary.
    """

    error_code: str  # e.g. 'invalid_credentials', 'group_not_found', 'pick_clock_skew'
    message: str
    request_id: str | None = None
