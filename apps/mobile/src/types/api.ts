// snake_case throughout — matches BE Pydantic wire format per CLAUDE.md

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  access_expires_at: string;
  refresh_expires_at: string;
}

export interface UserOut {
  id: string;
  auth_provider: "local" | "apple" | "google";
  email: string | null;
  display_name: string | null;
  avatar_color: string;
  created_at: string;
  last_login_at: string | null;
}

export interface AuthResponse {
  tokens: TokenPair;
  user: UserOut;
}

export interface ErrorResponse {
  error_code: string;
  message: string;
  request_id: string | null;
}

// ─── Groups ──────────────────────────────────────────────────────────────────

export interface GroupCreateResponse {
  group_id: string;
  name: string;
  invite_code: string;
  event_id: string;
  created_by_user_id: string;
  created_at: string;
  member_id: string;
}

export interface MemberOut {
  member_id: string;
  user_id: string;
  group_id: string;
  display_name: string;
  display_name_override: string | null;
  avatar_color: string;
  joined_at: string;
}

export interface MyGroupListItem {
  group_id: string;
  name: string;
  invite_code: string;
  event_id: string;
  created_by_user_id: string;
  last_active_at: string;
  archived_at: string | null;
  member_id: string;
  joined_at: string;
}

export interface MyGroupListResponse {
  groups: MyGroupListItem[];
}

export interface GroupJoinResponse {
  group: MyGroupListItem;
  member: MemberOut;
  is_new_member: boolean;
}

export interface GroupLeaveResponse {
  group_id: string;
  invite_code: string;
  left_at: string;
}

// ─── Events ──────────────────────────────────────────────────────────────────

export interface EventSummary {
  event_id: string;
  name: string;
  start_date: string;
  end_date: string;
  location: string | null;
  timezone: string;
}

export interface EventListItem {
  event_id: string;
  name: string;
  start_date: string;
  end_date: string;
  location: string | null;
  timezone: string;
}

export interface EventListResponse {
  events: EventListItem[];
}

export interface ArtistRef {
  artist_id: string;
  name: string;
  position: number;
  spotify_artist_id: string | null;
}

export interface SetDetail {
  set_id: string;
  display_name: string;
  day_label: string;
  starts_at: string;
  ends_at: string;
  artists: ArtistRef[];
}

export interface StageDetail {
  stage_id: string;
  name: string;
  display_order: number;
  color_hex: string | null;
  sets: SetDetail[];
}

export interface EventLineupResponse {
  event_id: string;
  name: string;
  start_date: string;
  end_date: string;
  location: string | null;
  timezone: string;
  stages: StageDetail[];
  sets: SetDetail[];
}

// ─── Group State ──────────────────────────────────────────────────────────────

export interface PickSummary {
  member_id: string;
  set_id: string;
  state: string;
  state_clock_ms: number;
}

export interface GroupStateResponse {
  group_id: string;
  invite_code: string;
  name: string;
  event: EventSummary;
  members: MemberOut[];
  picks: PickSummary[];
  archived_at: string | null;
  last_active_at: string;
}

// ─── Snapshot ────────────────────────────────────────────────────────────────

export interface SnapshotMember {
  user_id: string;
  member_id: string;
  display_name: string;
  avatar_color: string;
}

export interface SnapshotSet {
  set_id: string;
  display_name: string;
  artist_names: string[];
  day_label: string;
  starts_at: string;
  ends_at: string;
  pickers: SnapshotMember[];
}

export interface SnapshotStage {
  stage_id: string;
  name: string;
  display_order: number;
  sets: SnapshotSet[];
}

export interface GroupSnapshotResponse {
  group_id: string;
  invite_code: string;
  group_name: string;
  event_id: string;
  event_name: string;
  timezone: string;
  snapshot_at: string;
  window_minutes: number;
  members_total: number;
  stages: SnapshotStage[];
}

// ─── Artists ─────────────────────────────────────────────────────────────────

export interface TopTrack {
  name: string;
  preview_url: string | null;
  external_url: string | null;
}

export interface SimilarArtist {
  name: string;
  similarity: number | null;
}

export interface ArtistDetailResponse {
  artist_name: string;
  spotify_artist_id: string | null;
  image_url: string | null;
  genres: string[];
  similar_artists: SimilarArtist[];
  top_track: TopTrack | null;
  cache_status: "fresh" | "stale" | "miss";
  similarity_source: string | null;
  fetched_at: string | null;
}

// ─── Picks ───────────────────────────────────────────────────────────────────

export interface PickCreate {
  set_id: string;
  state: "active";
  state_clock_ms: number;
}

export interface PickResult {
  member_id: string;
  set_id: string;
  state: string;
  state_clock_ms: number;
  accepted: boolean;
}
