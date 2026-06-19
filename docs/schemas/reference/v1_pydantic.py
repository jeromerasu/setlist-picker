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
  /auth/{signup,login,refresh,apple,google} requires
  Authorization: Bearer <access_token>.
- Group-scoped endpoints additionally require the caller to be a Member of the
  group identified by the path's invite_code; the server derives member_id from
  (current_user.id, group.id) — clients do NOT send member_id. Leaving a group
  hard-deletes the Member row and cascades to picks (ADR-006 § 4.28).

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


class AuthProvider(str, Enum):
    """Mirror of user.auth_provider (ADR-006 § 2.1, § 4.20, § 4.24).

    All three values are live in v1: local (username/password), apple
    (Sign In with Apple, iOS), google (Google Sign-In, Android + iOS).
    """

    local = "local"
    apple = "apple"
    google = "google"


class DevicePlatform(str, Enum):
    """Mirror of device.platform (ADR-006 § 2.12, § 4.26)."""

    ios = "ios"
    android = "android"


class PushProvider(str, Enum):
    """Mirror of device.push_provider (ADR-006 § 2.12, § 4.26).

    v1 only writes `expo`; apns/fcm exist so a future migration off Expo
    doesn't require a schema change.
    """

    expo = "expo"
    apns = "apns"
    fcm = "fcm"


class ActivityKind(str, Enum):
    """Mirror of group_activity.kind (ADR-006 § 2.13, § 4.27)."""

    group_created = "group_created"
    member_joined = "member_joined"
    member_left = "member_left"
    pick_added = "pick_added"
    pick_removed = "pick_removed"


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
    """Local-auth signup payload. Server lowercases username/email before storing.

    Display name is stored as-typed — emojis preserved, casing preserved (ADR-006
    § 4.21). Validation just bounds length.
    """

    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=80)


class UserLogin(_Model):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class AppleSignInRequest(_Model):
    """POST /api/auth/apple — native Sign In with Apple flow (ADR-006 § 4.20).

    The native client (via expo-apple-authentication) invokes Apple's
    authorization, receives an identity token (JWT signed by Apple), and POSTs
    it here. The server validates the token against Apple's JWKS, extracts
    `sub`, then matches or creates the User.

    `display_name` and `email` are provided by Apple ONLY on the user's first
    sign-in to this app — the client forwards them on first auth and not after.
    Server treats both as optional and ignores them if a User already exists for
    the Apple `sub`.
    """

    identity_token: str  # The Apple-signed JWT
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None


class GoogleSignInRequest(_Model):
    """POST /api/auth/google — native Google Sign-In flow (ADR-006 § 4.24).

    Mirror of AppleSignInRequest. The native client invokes Google's auth flow
    (via expo-auth-session or Google's native SDK), receives an ID token (JWT
    signed by Google), and POSTs it here. The server validates against Google's
    JWKS (`https://www.googleapis.com/oauth2/v3/certs`), checks
    `iss == https://accounts.google.com` and `aud` matches our Google client id,
    extracts `sub`, then matches or creates the User.

    `display_name` and `email` are forwarded from Google's response; the server
    uses them only on first sign-in for a given `sub`.
    """

    id_token: str  # The Google-signed JWT
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None


class UserOut(_Model):
    """Public-facing user shape returned by auth and /users/me endpoints.

    `username` is null for SSO-provider users (ADR-006 § 2.1). `display_name`
    falls back to `username` on the FE when both are present.
    """

    id: UUID
    auth_provider: AuthProvider
    username: str | None  # always lowercase on the wire when present
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
    """Per-group membership identity. Used in join responses and group state.

    Hard-delete on leave (ADR-006 § 4.28): no `left_at`. Re-joining after a
    Leave creates a fresh Member row with a new `member_id`.
    """

    member_id: UUID
    user_id: UUID
    group_id: UUID
    display_name: str  # resolved: override → user.display_name → user.username
    display_name_override: str | None
    avatar_color: str
    joined_at: datetime


class GroupJoinResponse(_Model):
    group: MyGroupListItem
    member: MemberOut
    is_new_member: bool  # False if the user was already a Member.


# ---------------------------------------------------------------------------
# POST /api/groups/{invite_code}/leave — HARD-delete the calling Member
# ---------------------------------------------------------------------------
# No request body (current_user + path identifies the Member). Cascades to
# the caller's picks for this group (ADR-006 § 4.28). The FE MUST show a
# confirmation dialog ("Leave group? Your picks will be deleted.") before
# invoking this endpoint.


class GroupLeaveResponse(_Model):
    deleted_member_id: UUID
    deleted_pick_count: int  # how many picks were cascaded
    left_at: datetime  # server-clock time of the delete (audit / UI toast)


# ---------------------------------------------------------------------------
# GET /api/groups/{invite_code} — group state (members + picks)
# ---------------------------------------------------------------------------
# Polled every 15s per ADR-006 § 4.14. Supports If-Modified-Since → 304.


class PickSummary(_Model):
    """Tombstoned picks ARE included so the FE can reconcile its local queue
    (expo-sqlite per ADR-004).
    """

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
# Drains the expo-sqlite `pending_pick_op` table on reconnect (ADR-004).


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
    spotify_artist_id: str | None = None  # ADR-006 § 4.29 — trust-latest on import
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
#
# Conditional GET (ADR-006 § 4.14). The server returns a `Last-Modified` header
# computed from `MAX(pick.server_last_updated_at, member.joined_at,
# member.left_at)` for the group. The mobile client sends
# `If-Modified-Since: <previous Last-Modified>`. On no change the server
# returns 304 Not Modified with no body — critical on metered mobile data.
# The implementation may upgrade to `ETag` (hash of the rendered payload)
# later without a wire change.
# Same convention applies to GET /api/groups/{invite_code} (the polled
# group-state endpoint, 15s cadence).


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
# POST /api/users/me/devices — register a push token (ADR-006 § 2.12, § 4.26)
# ---------------------------------------------------------------------------
# v1 ships the table + endpoint shape but the send pipeline is post-V001.
# Clients (Expo) call this on app launch + on push-permission grant, so the
# token registry is hot the moment we start sending notifications.


class DeviceRegisterRequest(_Model):
    """Idempotent on (user_id, push_token) — re-registering the same token
    bumps `last_seen_at` rather than inserting a duplicate row.
    """

    platform: DevicePlatform
    push_token: str = Field(min_length=1, max_length=4096)
    push_provider: PushProvider = PushProvider.expo  # v1: always expo


class DeviceOut(_Model):
    device_id: UUID
    user_id: UUID
    platform: DevicePlatform
    push_provider: PushProvider
    created_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None


class DeviceListResponse(_Model):
    devices: list[DeviceOut]


# ---------------------------------------------------------------------------
# DELETE /api/users/me/devices/{device_id} — revoke a push token
# ---------------------------------------------------------------------------
# Marks revoked_at = now(). The row is retained for audit; the send pipeline
# filters on `revoked_at IS NULL`.


class DeviceRevokeResponse(_Model):
    device_id: UUID
    revoked_at: datetime


# ---------------------------------------------------------------------------
# GET /api/groups/{invite_code}/activity — group activity feed
# ---------------------------------------------------------------------------
# ADR-006 § 2.13, § 4.27. Reads `group_activity` ordered DESC. Pruning is a
# server-side cron (out of scope V001); see ADR-006 § 4.27 for the rule.


class GroupActivityItem(_Model):
    """One row of group_activity.

    `payload` is kind-specific (ADR-006 § 4.27 table) — display name and
    avatar color are denormalized in `payload` so the feed renders without
    JOINs against `user` (and survives a `member_left` row outliving its
    Member due to the SET NULL FK).
    """

    activity_id: UUID
    group_id: UUID
    member_id: UUID | None  # NULL once the Member row is deleted (member_left).
    kind: ActivityKind
    payload: dict[str, object]
    created_at: datetime


class GroupActivityListResponse(_Model):
    items: list[GroupActivityItem]
    # Cursor pagination: opaque token of the oldest item's created_at + id.
    next_cursor: str | None = None


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
