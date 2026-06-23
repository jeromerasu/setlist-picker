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
  username: string | null;
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

export interface GroupCreateResponse {
  invite_code: string;
  group_id: string;
}

export interface MemberOut {
  member_id: string;
  display_name: string;
  avatar_color: string;
}

export interface EventSummary {
  event_id: string;
  name: string;
  start_date: string;
  end_date: string;
}

export interface MyGroupListItem {
  invite_code: string;
  group_name: string;
  event: EventSummary | null;
  member_count: number;
  my_pick_count: number;
  last_active_at: string;
}

export interface MyGroupListResponse {
  groups: MyGroupListItem[];
}

export interface ArtistRef {
  artist_id: string;
  name: string;
  spotify_artist_id: string | null;
  image_url: string | null;
}

export interface SetDetail {
  set_id: string;
  name: string;
  start_time: string | null;
  end_time: string | null;
  artists: ArtistRef[];
}

export interface StageDetail {
  stage_id: string;
  name: string;
  color: string | null;
  sets: SetDetail[];
}

export interface EventLineupResponse {
  event_id: string;
  name: string;
  start_date: string;
  end_date: string;
  stages: StageDetail[];
}

export interface PickCreate {
  group_code: string;
  set_id: string;
  member_name: string;
}

export interface PickResult {
  pick_id: string;
  set_id: string;
  member_name: string;
  picked_at: string;
}
