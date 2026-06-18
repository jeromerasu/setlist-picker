"""
v1 Pydantic reference shapes — companion to ADR-006.

THIS FILE IS A DESIGN ARTIFACT. It is intentionally NOT imported anywhere in
services/api/. The Phase 1 implementer reads this file and copies / adapts
these shapes into the actual FastAPI Pydantic models. Until then, this file is
the canonical wire-shape reference.

Conventions (per CLAUDE.md and ADR-006):

- snake_case field names everywhere (Pydantic v2 default).
- TZ-aware datetimes. The wire format is ISO-8601 with offset.
- Pick state_clock_ms is the client-assigned Unix epoch ms; see ADR-006 § 4.5.
- Request models and response models are intentionally separate even when they
  look similar — request/response surfaces drift over time.
- Models below are grouped by endpoint, in the order they appear in
  ARCHITECTURE.md § API surface plus the additions called out in the feature
  specs (rename, leave, bulk pick sync).

Mypy-strict-clean and ruff-clean as written.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class _Model(BaseModel):
    """Project base: forbid unknown fields on input, populate cleanly on output."""

    model_config = ConfigDict(extra="forbid", frozen=False)


class PickState(str, Enum):
    """Mirror of pick.state. Stored as string per ADR-006 § 2.9."""

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


class SocialLinks(_Model):
    """Loose-shape artist social links from the lineup adapter.

    All fields optional — different sources populate different subsets.
    Field set verified against .local-data/tml26-w2.json.
    """

    spotify: str | None = None
    instagram: str | None = None
    soundcloud: str | None = None
    tiktok: str | None = None
    twitter: str | None = None
    facebook: str | None = None
    youtube: str | None = None
    website: str | None = None


# ---------------------------------------------------------------------------
# POST /api/groups — create a group
# ---------------------------------------------------------------------------


class CreateGroupRequest(_Model):
    """Optional: pass an initial name. Defaults to 'Friends 🎵' server-side."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    event_id: UUID  # v1: one group ↔ one event; the FE picks which event to attach.


class CreateGroupResponse(_Model):
    group_code: str = Field(min_length=8, max_length=8)
    name: str
    event_id: UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# POST /api/groups/{code}/join — join as a display name
# ---------------------------------------------------------------------------


class JoinGroupRequest(_Model):
    display_name: str = Field(min_length=1, max_length=40)
    # Client-generated UUIDv7 so offline-first join works; server validates the
    # UUID is well-formed and not already taken in this group. See ADR-006 § 4.1.
    member_id: UUID


class JoinGroupResponse(_Model):
    member_id: UUID
    group_code: str
    display_name: str
    color_hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    joined_at: datetime


# ---------------------------------------------------------------------------
# GET /api/groups/{code} — group state (members + picks)
# ---------------------------------------------------------------------------


class MemberSummary(_Model):
    """Embedded in GroupStateResponse and in the lineup-detail member dots."""

    member_id: UUID
    display_name: str
    color_hex: str
    joined_at: datetime
    left_at: datetime | None = None


class PickSummary(_Model):
    """Tombstoned picks ARE included so the FE can reconcile its IndexedDB queue.

    The FE will typically filter to state=active for rendering; tombstones are
    needed for the LWW comparison on the client side.
    """

    member_id: UUID
    set_id: UUID
    state: PickState
    state_clock_ms: int = Field(ge=0)


class EventSummary(_Model):
    """Embedded in GroupStateResponse — saves the FE a second call (see § 5.5)."""

    event_id: UUID
    name: str
    start_date: date
    end_date: date
    location: str | None
    timezone: str  # IANA, e.g. "Europe/Brussels"


class GroupStateResponse(_Model):
    group_code: str
    name: str
    event: EventSummary
    members: list[MemberSummary]
    picks: list[PickSummary]
    archived_at: datetime | None
    last_active_at: datetime


# ---------------------------------------------------------------------------
# PATCH /api/groups/{code} — rename
# ---------------------------------------------------------------------------


class RenameGroupRequest(_Model):
    name: str = Field(min_length=1, max_length=80)


class RenameGroupResponse(_Model):
    group_code: str
    name: str


# ---------------------------------------------------------------------------
# POST /api/groups/{code}/leave — soft-remove the calling member
# ---------------------------------------------------------------------------


class LeaveGroupRequest(_Model):
    member_id: UUID


class LeaveGroupResponse(_Model):
    member_id: UUID
    left_at: datetime


# ---------------------------------------------------------------------------
# POST /api/groups/{code}/picks — add (or upsert) a pick
# ---------------------------------------------------------------------------


class PickToggleRequest(_Model):
    """Single pick toggle. The LWW comparison runs server-side per ADR-006 § 4.5."""

    member_id: UUID
    set_id: UUID
    state: PickState
    state_clock_ms: int = Field(ge=0)


class PickToggleResponse(_Model):
    """The server returns the final accepted state (which may differ from the
    request if the incoming clock was older than what was already stored).
    """

    member_id: UUID
    set_id: UUID
    state: PickState
    state_clock_ms: int
    accepted: bool  # False if the incoming clock lost the LWW comparison.


# ---------------------------------------------------------------------------
# POST /api/groups/{code}/picks/sync — bulk drain of the offline queue
# ---------------------------------------------------------------------------


class PickSyncRequest(_Model):
    """The IndexedDB queue contents from ADR-004, sent in order."""

    member_id: UUID  # the calling member; all toggles must match.
    toggles: list[PickToggleRequest]


class PickSyncResponse(_Model):
    accepted: list[PickToggleResponse]
    # No separate `rejected` list — rejections appear in `accepted` with
    # accepted=False, so the FE can update its local state uniformly.


# ---------------------------------------------------------------------------
# DELETE /api/groups/{code}/picks/{set_id} — explicit unpick (online flow)
# ---------------------------------------------------------------------------


class PickRemoveRequest(_Model):
    """For online unpick the FE generates a fresh clock and sends it here.
    Equivalent to POSTing /picks with state=tombstoned.
    """

    member_id: UUID
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
    """Embedded in SetDetail. Lean shape; full drill-down comes from
    GET /api/artists/{artist_name}.
    """

    artist_id: UUID
    name: str
    position: int = Field(ge=0)
    image_url: str | None = None
    social_links: SocialLinks | None = None


class SetDetail(_Model):
    set_id: UUID
    stage_id: UUID
    display_name: str
    day_label: str  # FRIDAY / SATURDAY / SUNDAY (source-provided)
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
    """Mirrors the source JSON artist shape (e.g. tml26-w2.json).

    Verified field set: every key from the source maps to an optional field
    here. The adapter is responsible for translating this into Artist +
    ArtistSourceRef + (eventually) set_artist rows.
    """

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
    """One row from `performances[]` in the source JSON."""

    id: str
    name: str  # may differ from artists[0].name for b2b sets
    artists: list[LineupSourceArtist] = Field(min_length=1)
    stage: LineupSourceStage
    date: date  # source provides as 'YYYY-MM-DD'
    day: str  # FRIDAY / SATURDAY / SUNDAY
    startTime: str  # ISO-8601 with offset, source-formatted as 'YYYY-MM-DD HH:MM:SS+HH:MM'
    endTime: str


class LineupImportRequest(_Model):
    """Admin paste-import payload. Token-gated per PRD § 5.5."""

    event_name: str
    start_date: date
    end_date: date
    timezone: str  # IANA
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
# GET /api/groups/{code}/snapshot — screenshotable "where will we be at T" view
# ---------------------------------------------------------------------------
# Powers the share-as-screenshot use case from ADR-006 § 4.15. The wire shape
# denormalizes member names, artist names, and stage names ONTO the payload
# so a captured screenshot is self-explanatory without further lookups.


class SnapshotMember(_Model):
    """A picker, embedded directly on each set in the snapshot payload."""

    member_id: UUID
    display_name: str
    color_hex: str


class SnapshotSet(_Model):
    """One set within the snapshot window.

    `artist_names` is denormalized so the screenshot view doesn't have to join
    against `set_artist` and `artist` at render time. Order matches
    set_artist.position (source-provided).
    """

    set_id: UUID
    display_name: str
    artist_names: list[str] = Field(min_length=1)
    day_label: str
    starts_at: datetime
    ends_at: datetime
    pickers: list[SnapshotMember]


class SnapshotStage(_Model):
    """One stage column in the snapshot. Sets ordered by starts_at ascending."""

    stage_id: UUID
    name: str
    display_order: int
    sets: list[SnapshotSet]


class GroupSnapshotResponse(_Model):
    """The complete payload behind a single screenshot.

    Designed to render onto one screen and be intelligible without context.
    Includes every field the screenshot's recipient might lack: group name,
    event name, IANA timezone, the exact window the payload represents.
    """

    group_code: str
    group_name: str
    event_id: UUID
    event_name: str
    timezone: str  # IANA — recipient may be in a different tz; FE renders local.
    snapshot_at: datetime  # the `at` parameter (server-clamped if missing).
    window_minutes: int
    members_total: int  # convenience: "5 of 8 friends going" headline.
    stages: list[SnapshotStage]  # ordered by stage.display_order.


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
    """Per features/artist-drilldown-spec § API contract."""

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
    log full tracebacks via logger.exception(...); the wire body is just the
    summary.
    """

    error_code: str  # e.g. 'group_not_found', 'pick_clock_skew'
    message: str
    request_id: str | None = None
