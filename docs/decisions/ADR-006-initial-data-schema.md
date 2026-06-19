# ADR-006: Initial data schema + auth model (V001 baseline)

## Status
**Accepted (2026-06-18).** Five product decisions ratified by Jerome on 2026-06-18 are now locked into this ADR; the auth model is locked to Option C (Apple + Google + local). Companion supersessions land in the same PR: [ADR-001 (tech stack)](ADR-001-tech-stack.md) goes to Postgres-from-start + RN/Expo, and [ADR-004 (offline strategy)](ADR-004-offline-strategy.md) goes to `expo-sqlite` + AsyncStorage.

This ADR **supersedes [ADR-003](ADR-003-auth-model.md)**: the v1 product ships with authenticated user accounts (username + password + JWT, with Apple Sign-In and Google Sign-In as first-class alternatives), not anonymous per-device members.

> **PRD alignment required** — the current [PRD § 1, § 2, § 4](../PRD.md) commits to "no account, no email, no signup, under 30 seconds from invite to first pick." That language predates this pivot. **Sign-off on this ADR implies a follow-up PR to align the PRD.** PRD update remains out of scope for this PR to keep the diff focused on the schema + auth design.

## Context

Phase 1 of the [ROADMAP](../ROADMAP.md) creates the FastAPI skeleton and the first Alembic migration. Every backend ticket — auth, group lifecycle, pick sync, lineup import, artist drill-down, screenshot snapshot — depends on the V001 schema landing first.

The pivot from ADR-003's anonymous model is driven by:

- **Cross-device sync.** ADR-003's "phone and laptop joining as Jerome are two distinct presences" worked for v1 anonymity but breaks the core "where is everyone right now?" promise when one user's picks split across devices.
- **Screenshot-share UX.** The snapshot endpoint (§ 4.13) returns a per-stage view annotated with picker names; resolving stable identities improves the screenshot's value when shared.
- **Real-ish-time visibility into the whole group's pick history** — Jerome confirmed in the 2026-06-18 product clarification that picks are server-authoritative, every member can read every other member's picks, and the server is the source of truth for groups + members + picks.

This ADR must support:

- Authenticated user identity (username + password AND Apple Sign-In AND Google Sign-In; JWT-based session) — § Auth model below.
- Group lifecycle, **scoped to exactly one Event per Group** (§ 4.25), with an invite code distinct from the internal group id ([calendar-spec](../features/calendar-spec.md), [friends-list-spec](../features/friends-list-spec.md)).
- Per-set member picks with last-write-wins reconciliation ([ADR-004](ADR-004-offline-strategy.md)).
- Artist drill-down with cache + fallback chain ([ADR-005](ADR-005-music-data-source.md)).
- A `device` table for push tokens — empty surface in v1 (no push notifications yet), but the table ships in V001 so push lands as an app-layer feature without a future migration (§ 4.26).
- A `group_activity` log table for in-group event feed — ships in V001; pruned periodically (§ 4.27).
- Lossless round-trip of the source lineup JSON under the adapter pattern — verified against [`.local-data/tml26-w2.json`](../../.local-data/tml26-w2.json) (405 performances, 15 stages, 420 artists, 35 b2b sets, 27 sets straddling midnight, 73 sets whose display name differs from the headlining artist name).

### Mobile-native direction (2026-06-18 locked)

V1 ships as a native React Native + Expo app on both iOS and Android. [ADR-001 (Tech stack)](ADR-001-tech-stack.md) was revised on 2026-06-18 to lock this in, and [ADR-004 (Offline strategy)](ADR-004-offline-strategy.md) was revised in parallel to drop IndexedDB + Workbox in favor of `expo-sqlite` + AsyncStorage. The data schema in this ADR is platform-agnostic; what the mobile direction shapes here:

- Apple Sign-In is v1 (App Store Guideline 4.8) — schema columns + flow in § 4.20.
- Google Sign-In is v1 (Android table stakes; avoids Android friction) — schema columns + flow in § 4.24.
- The offline client-side store on mobile is `expo-sqlite` + AsyncStorage, not IndexedDB — see [ADR-004](ADR-004-offline-strategy.md). The Pick LWW algorithm (§ 4.5) is unchanged.
- Push notifications are deferred to a v1.x ticket; the `device` table is in V001 so when push lands it's app-layer-only (§ 4.26).
- Display name handling on mobile keyboards (emoji + case) — § 4.21.
- Invite code UX via Share Sheet — § 4.22 confirms 8-char Crockford base32.

### Canonical UX flow (post-pivot)

1. New visitor → signup with `{username, password, email?, display_name?}`, OR Apple Sign-In, OR Google Sign-In. Returns user + access/refresh JWT pair.
2. Returning visitor → login by username/password OR re-auth via Apple / Google. Returns user + JWT pair.
3. Authenticated user creates a group → **the FE forces the user to pick an Event up front** (§ 4.25; group is 1:1 with event). Server returns the new group + the 8-char Crockford base32 invite code + auto-creates the creator's Member row.
4. Authenticated user shares the invite code out-of-band (Share Sheet).
5. Authenticated friend joins via `POST /api/groups/join` with `{invite_code, display_name_override?}` → server creates a Member row scoped to that User + Group, or returns the existing Member if the user already joined.
6. Each User sees `GET /api/users/me/groups` — every group the user is a Member of, sourced server-side (not localStorage). Token-authed; no client-side roster.
7. Inside a group: festival calendar with per-set picker dots. Picks server-authoritative, polled by the FE; cross-device sync is automatic because picks are scoped to Member (= User × Group), not to device.
8. Tap an artist → drill-down ([ADR-005](ADR-005-music-data-source.md)).
9. Pick = "I'm going to this set." Public within the group (§ 4.12).
10. **Screenshotable "where will we be at time T" view** — the snapshot endpoint (§ 4.13) returns picks from **all** group members with display names + avatar colors denormalized for self-contained screen captures. **No `event_id` query param** — the group implies it (§ 4.25).
11. **Leave group** — hard delete (§ 4.28). FE shows a confirmation dialog ("Leave group? Your picks will be deleted.") before the destructive call.

The [ARCHITECTURE.md § Data model](../ARCHITECTURE.md) block has been slim-summarized; this ADR is the authoritative source from here forward.

---

## 1. Auth model

### 1.1 Identity

- **User** is the account of record (§ 2.1). One human → one User → potentially many Members (one per Group).
- **Member** is the per-Group join row (§ 2.3). Owns the picks via FK. Optionally carries a per-group display-name override.
- **Group** owns the invite code that propagates new Members (§ 2.2).
- **Device** is the per-device push registration (§ 2.12). One User → potentially many Devices.

### 1.2 Credentials

- **Username** — required at signup for `local` auth_provider, unique. Stored lowercased; comparisons run `LOWER() = LOWER()` on both sides. Eliminates the classic "Jerome registered, jerome login fails" bug class (a reasonable engineer's lesson; documented here so it doesn't repeat). § 4.16.
- **Password** — argon2id hash. § 4.17.
- **Email** — optional in v1 for `local` users. Without email there's no password-reset flow; users who forget their password contact support (manual reset). § 4.18.
- **Apple identity** — `apple_subject_id` populated from Apple's identity-token `sub` claim. § 4.20.
- **Google identity** — `google_subject_id` populated from Google's ID-token `sub` claim. § 4.24.

### 1.3 Session

- **JWT** (HS256, secret in env var `JWT_SECRET`).
- **Access token** — 24h lifetime. Claims: `sub` = `user.id` (string), `iat`, `exp`, `type: "access"`.
- **Refresh token** — 7d lifetime. Claims: `sub`, `iat`, `exp`, `type: "refresh"`, `jti` (refresh-token id for v2 revocation).
- `POST /api/auth/refresh` exchanges a valid refresh token for a new access+refresh pair. v1 does **not** track refresh-token revocation (no `refresh_token` table) — flagged in § 5.

### 1.4 Middleware

- Every endpoint except `POST /api/auth/{signup,login,refresh,apple,google}` requires a valid access token in `Authorization: Bearer <token>`.
- FastAPI dependency `current_user: User` decodes the JWT, looks up the User by `sub`, returns the row (404 / 401 on failure).
- **Group-scoped endpoints** additionally check that `current_user` has a Member row for the group. On miss → 403.
- Picks: the request body does **not** carry a `member_id`. The server derives it from `(current_user.id, group_id)`. Prevents one user posting picks on another's behalf.

### 1.5 Forward compat

- **Apple Sign-In and Google Sign-In** ship in V001 (§ 4.20, § 4.24). No "reserved" provider values.
- **Refresh-token revocation** — additive `refresh_token` table later; current `jti` claim makes it possible without a JWT schema change.
- **Email-based password reset** — v2; would require SMTP integration and a `password_reset_token` table.
- **Push notifications** — `device` table is in V001 (§ 2.12). Send pipeline lands when push is in scope; no schema migration needed.

---

## 2. Tables (V001)

V001 ships **13 tables**: `user`, `group`, `member`, `device`, `event`, `stage`, `set`, `artist`, `artist_source_ref`, `set_artist`, `pick`, `artist_cache`, `group_activity`.

Conventions:

- **Primary keys** are UUIDv7 (16-byte binary in Postgres). Rationale: § 4.1.
- **Timestamps with timezone** are `TIMESTAMPTZ`.
- **JSON columns** are `JSONB`. Postgres-from-start per [ADR-001](ADR-001-tech-stack.md) (2026-06-18 revision) — no SQLite dialect hedging.
- **`source_adapter`** identifies a lineup adapter, e.g. `event_api_v1`, `manual`.

### 2.1 `user`

The account of record. Server-authoritative identity; survives device wipes.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `id` | `UUID` | NO | (UUIDv7) | § 4.1. |
| `auth_provider` | `TEXT` | NO | `'local'` | Enum: `local` \| `apple` \| `google`. Identifies the signup path. App-layer-enforced enum. § 4.20, § 4.24. |
| `username` | `TEXT` | YES | NULL | Stored lowercased; the comparison key on login for `local` users. Length 3–32, [a-z0-9_-] only. NULL for SSO-provider users (they sign in via the provider, not by username). § 4.16. |
| `email` | `TEXT` | YES | NULL | Stored lowercased when present. Optional for `local` users (§ 4.18). Apple may return a private-relay address (`*@privaterelay.appleid.com`); we store it verbatim and treat it the same. |
| `password_hash` | `TEXT` | YES | NULL | Argon2id-encoded string. Required for `local`; NULL for SSO. § 4.17. |
| `apple_subject_id` | `TEXT` | YES | NULL | Apple's stable identifier from the Sign In with Apple identity token's `sub` claim. NULL unless `auth_provider = 'apple'`. § 4.20. |
| `google_subject_id` | `TEXT` | YES | NULL | Google's stable identifier from the Google ID-token's `sub` claim. NULL unless `auth_provider = 'google'`. § 4.24. |
| `display_name` | `TEXT` | YES | NULL | UI-facing name. Falls back to `username` when null. Stored as-typed — emojis and casing preserved (§ 4.21). |
| `avatar_color` | `CHAR(7)` | NO | — | `#RRGGBB`. Picked at signup from a default palette; user can change. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | Updated by app code on any User mutation. |
| `last_login_at` | `TIMESTAMPTZ` | YES | NULL | Updated by `/auth/login`, `/auth/apple`, or `/auth/google`. |

App-layer invariants (no DB CHECK constraints — keep app-layer enforcement consistent across providers):

- `auth_provider = 'local'` ⇒ `username IS NOT NULL` AND `password_hash IS NOT NULL` AND `apple_subject_id IS NULL` AND `google_subject_id IS NULL`.
- `auth_provider = 'apple'` ⇒ `apple_subject_id IS NOT NULL` AND `password_hash IS NULL` AND `google_subject_id IS NULL`.
- `auth_provider = 'google'` ⇒ `google_subject_id IS NOT NULL` AND `password_hash IS NULL` AND `apple_subject_id IS NULL`.

Indexes:

- PK `(id)`.
- `uq_user_username (username) WHERE username IS NOT NULL` — partial unique; case-insensitive **at the application layer** because we store lowercased (§ 4.16).
- `uq_user_email (email) WHERE email IS NOT NULL` — partial unique.
- `uq_user_apple_subject (apple_subject_id) WHERE apple_subject_id IS NOT NULL` — partial unique. The Apple `sub` claim is globally unique within Apple's identity system; this index matches one User to one Apple identity.
- `uq_user_google_subject (google_subject_id) WHERE google_subject_id IS NOT NULL` — partial unique. Google's `sub` is globally unique within Google's identity system; mirror of the Apple index.

FKs: none.

### 2.2 `group`

The shared coordination unit. **Scoped to exactly one Event** (§ 4.25). Owned by a creator User.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `id` | `UUID` | NO | (UUIDv7) | § 4.1. Internal identifier. |
| `name` | `TEXT` | NO | `'Friends 🎵'` | Group's display name. |
| `invite_code` | `CHAR(8)` | NO | (assigned) | 8-char Crockford base32 ([PRD § 5.1](../PRD.md)); the URL-facing code (`/g/AB7K9MNP`). The invite IS the code — § 4.11. |
| `event_id` | `UUID` | **NO** | — | **One group ↔ one event (NOT NULL, FK to `event`).** Locked by § 4.25. |
| `created_by_user_id` | `UUID` | NO | — | Creator User. Useful for "you created this group" UI and future creator-only mutations. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | Group creation. |
| `last_active_at` | `TIMESTAMPTZ` | NO | `now()` | Updated on any group write. Drives 90-day archival sweep. |
| `archived_at` | `TIMESTAMPTZ` | YES | NULL | NULL = active. |

Indexes:

- PK `(id)`.
- `uq_group_invite_code (invite_code)` — unique; the URL → group resolution.
- `idx_group_archive_sweep (last_active_at) WHERE archived_at IS NULL` — partial; archival sweep.
- `idx_group_event (event_id)` — supports "list groups for event X" admin queries.

FKs: `event_id → event(event_id)`; `created_by_user_id → user(id)`.

### 2.3 `member` (hard-delete on leave)

A User's membership in a Group. One row per `(user_id, group_id)` pair. **Leaving a group hard-deletes the Member row** (§ 4.28); cascades down to the User's picks in that group.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `id` | `UUID` | NO | (UUIDv7) | Surrogate PK so picks have a stable FK target. |
| `user_id` | `UUID` | NO | — | FK → user. |
| `group_id` | `UUID` | NO | — | FK → group. |
| `display_name_override` | `TEXT` | YES | NULL | Per-group nickname. Falls back to `user.display_name` → `user.username`. Lets "Jerome" be "JR" in one group. |
| `joined_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |

Indexes:

- PK `(id)`.
- `uq_member_user_group (user_id, group_id)` — unique; a User can only be a Member of a Group once. Re-joining after a hard delete creates a fresh row (different `id`).
- `idx_member_group (group_id)` — serves "list members of a group" (hot path: top-bar avatars).
- `idx_member_user (user_id)` — serves `GET /api/users/me/groups`.

FKs: `user_id → user(id)` ON DELETE CASCADE; `group_id → group(id)` ON DELETE CASCADE.

**Cascade outward:** `pick.member_id → member(id)` is itself `ON DELETE CASCADE` (§ 2.10). When a Member row is deleted (either explicitly by Leave, or transitively from User / Group deletion), every `pick` row for that Member is deleted with it. **The FE MUST show a confirmation dialog before invoking the Leave endpoint** ("Leave group? Your picks will be deleted.") — encoded as a forward-compat acceptance criterion (§ 4.28).

Note: avatar color is **not** per-Member. Resolved at query time from `user.avatar_color`. See § 4.12.

### 2.4 `event`

A festival edition. Unchanged from the pre-pivot draft.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `event_id` | `UUID` | NO | (UUIDv7) | § 4.1. |
| `name` | `TEXT` | NO | — | e.g. `Tomorrowland 2026 W2`. |
| `start_date` | `DATE` | NO | — | Local-date semantics. |
| `end_date` | `DATE` | NO | — | Inclusive. |
| `location` | `TEXT` | YES | NULL | Optional. |
| `timezone` | `TEXT` | NO | `'UTC'` | IANA name, e.g. `Europe/Brussels`. Drives day-boundary rendering — § 4.2. |
| `source_adapter` | `TEXT` | NO | `'manual'` | Lineup adapter. |
| `external_id` | `TEXT` | YES | NULL | Raw id from the adapter. |
| `imported_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |

Indexes: PK `(event_id)`; `uq_event_external (source_adapter, external_id) WHERE external_id IS NOT NULL`.

FKs: none.

### 2.5 `stage`

A stage within an event. Unchanged.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `stage_id` | `UUID` | NO | (UUIDv7) | Internal id, distinct from `external_id`. |
| `event_id` | `UUID` | NO | — | Scope. |
| `name` | `TEXT` | NO | — | e.g. `MAINSTAGE`. Verbatim from source. |
| `display_order` | `INTEGER` | NO | `0` | Calendar column order. |
| `external_id` | `TEXT` | NO | — | Raw id from the adapter. |

Indexes: PK `(stage_id)`; `uq_stage_external (event_id, external_id)`; `idx_stage_event_order (event_id, display_order)`.

FKs: `event_id → event(event_id)` ON DELETE CASCADE.

### 2.6 `set` (a.k.a. performance)

A single billed slot. Unchanged.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `set_id` | `UUID` | NO | (UUIDv7) | § 4.1. |
| `event_id` | `UUID` | NO | — | Denormalized for hot lineup queries. |
| `stage_id` | `UUID` | NO | — | Column on the calendar. |
| `display_name` | `TEXT` | NO | — | Billed name, verbatim from source. May differ from artist names for b2b. |
| `day_label` | `TEXT` | NO | — | Source-provided day (`FRIDAY` / `SATURDAY` / `SUNDAY`). Denormalized for FE day-tab grouping — § 4.2. |
| `starts_at` | `TIMESTAMPTZ` | NO | — | Authoritative absolute time. |
| `ends_at` | `TIMESTAMPTZ` | NO | — | Authoritative absolute time. May straddle midnight; may carry the source's `+1s` quirk. |
| `external_id` | `TEXT` | NO | — | Raw id from the adapter. |

Indexes: PK `(set_id)`; `uq_set_external (event_id, external_id)`; `idx_set_event_starts (event_id, starts_at)`; `idx_set_stage_starts (stage_id, starts_at)`.

FKs: `event_id → event(event_id)` ON DELETE CASCADE; `stage_id → stage(stage_id)` ON DELETE CASCADE.

### 2.7 `artist`

Global artist registry. Upsert on `name_normalized` per § 4.29.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `artist_id` | `UUID` | NO | (UUIDv7) | § 4.1. |
| `name` | `TEXT` | NO | — | Canonical display name. First-import wins. |
| `name_normalized` | `TEXT` | NO | — | `lower(NFKD(strip_diacritics(name))).strip()`, whitespace collapsed. Dedup key. |
| `spotify_artist_id` | `TEXT` | YES | NULL | Spotify's stable artist id (e.g. `4Z8W4fKeB5YxbusRsdQVPb`). **Trust-latest-non-null** on lineup re-import — § 4.29. |
| `image_url` | `TEXT` | YES | NULL | From source. |
| `social_links` | `JSONB` | YES | NULL | Loose-shape `{spotify, instagram, soundcloud, tiktok, twitter, facebook, youtube, website}`. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |

Indexes: PK `(artist_id)`; `uq_artist_name_normalized (name_normalized)`; `idx_artist_spotify (spotify_artist_id) WHERE spotify_artist_id IS NOT NULL`.

FKs: none.

### 2.8 `artist_source_ref`

Maps a global artist row to its raw id in each lineup source. Unchanged.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `artist_id` | `UUID` | NO | — | FK. |
| `source_adapter` | `TEXT` | NO | — | e.g. `event_api_v1`. |
| `external_id` | `TEXT` | NO | — | Raw id from that adapter. |

Indexes: PK `(artist_id, source_adapter)`; `uq_artist_source_ext (source_adapter, external_id)`.

FKs: `artist_id → artist(artist_id)` ON DELETE CASCADE.

### 2.9 `set_artist`

Many-to-many between Set and Artist. Position is significant. Unchanged.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `set_id` | `UUID` | NO | — | FK. |
| `artist_id` | `UUID` | NO | — | FK. |
| `position` | `INTEGER` | NO | — | 0-indexed; source-provided ordering. |

Indexes: PK `(set_id, artist_id)`; `uq_set_position (set_id, position)`; `idx_setartist_artist (artist_id)`.

FKs: `set_id → set(set_id)` ON DELETE CASCADE; `artist_id → artist(artist_id)` ON DELETE RESTRICT.

### 2.10 `pick`

A member's intention to attend a set. Tombstoned on unpick (§ 4.6). LWW reconciliation (§ 4.5). Hard-deleted when the owning Member is deleted (§ 2.3, § 4.28).

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `member_id` | `UUID` | NO | — | FK → member.id. **ON DELETE CASCADE** — Leave-group nukes the User's picks for that group. § 2.3. |
| `set_id` | `UUID` | NO | — | FK. |
| `state` | `TEXT` | NO | `'active'` | Enum: `active` \| `tombstoned`. |
| `state_clock_ms` | `BIGINT` | NO | — | Client-assigned epoch ms. LWW key. § 4.5. |
| `server_first_seen_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |
| `server_last_updated_at` | `TIMESTAMPTZ` | NO | `now()` | Audit + drives Last-Modified on snapshot. § 4.14. |

Indexes:

- PK `(member_id, set_id)`.
- `idx_pick_set_active (set_id) WHERE state = 'active'` — partial; per-set dot rendering.
- `idx_pick_member_active (member_id) WHERE state = 'active'` — partial; "my picks" / member-detail view.

FKs: `member_id → member(id)` **ON DELETE CASCADE**; `set_id → set(set_id)` ON DELETE CASCADE.

### 2.11 `artist_cache`

Spotify / Last.fm / heuristic data. Unchanged.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `name_normalized` | `TEXT` | NO | — | PK. Same normalization as `artist.name_normalized`. |
| `display_name` | `TEXT` | YES | NULL | UI fallback. |
| `spotify_artist_id` | `TEXT` | YES | NULL | Spotify ID once known (cache copy; the canonical column lives on `artist`). |
| `image_url` | `TEXT` | YES | NULL | Best image. |
| `genres` | `JSONB` | YES | NULL | `string[]`. |
| `similar_artists` | `JSONB` | YES | NULL | `[{name, similarity_source}]`. |
| `top_track` | `JSONB` | YES | NULL | `{name, preview_url, spotify_url, image_url}`. |
| `similarity_source` | `TEXT` | YES | NULL | `spotify_v2` \| `lastfm` \| `genre_overlap` \| `none`. |
| `fetched_at` | `TIMESTAMPTZ` | YES | NULL | Last successful fetch. |
| `fetch_failure_count` | `INTEGER` | NO | `0` | Backoff per [ADR-005](ADR-005-music-data-source.md). |
| `last_failure_at` | `TIMESTAMPTZ` | YES | NULL | Backoff timestamp. |

Indexes: PK `(name_normalized)`; `idx_artist_cache_fetched (fetched_at) WHERE fetched_at IS NOT NULL`.

FKs: none (intentional).

### 2.12 `device` (NEW — push token registry)

A push-token registration. One row per (User, device installation). v1 ships the table but does not yet send push notifications (§ 4.26).

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `id` | `UUID` | NO | (UUIDv7) | § 4.1. |
| `user_id` | `UUID` | NO | — | FK → user. |
| `platform` | `TEXT` | NO | — | App-layer-enforced enum: `ios` \| `android`. |
| `push_token` | `TEXT` | NO | — | The provider-issued token string. |
| `push_provider` | `TEXT` | NO | `'expo'` | App-layer-enforced enum: `expo` \| `apns` \| `fcm`. **v1 only writes `'expo'`** — Expo's push service handles APNS + FCM behind one token (§ 4.26). The other values exist so a future migration off Expo doesn't require a schema change. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |
| `last_seen_at` | `TIMESTAMPTZ` | NO | `now()` | Updated when the app foregrounds and re-registers. Drives stale-token sweep. |
| `revoked_at` | `TIMESTAMPTZ` | YES | NULL | NULL = active. Set when the provider returns "invalid token" or the user disables notifications. |

Indexes:

- PK `(id)`.
- `uq_device_user_token (user_id, push_token)` — a single push token per User can only register once.
- `idx_device_user_active (user_id) WHERE revoked_at IS NULL` — supports "send push to all of this user's active devices."

FKs: `user_id → user(id)` ON DELETE CASCADE.

### 2.13 `group_activity` (NEW — event feed)

Per-group activity feed. Backs the "what changed in this group?" view and the future push-notification trigger (§ 4.27).

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `id` | `UUID` | NO | (UUIDv7) | § 4.1. |
| `group_id` | `UUID` | NO | — | FK → group. |
| `member_id` | `UUID` | YES | NULL | FK → member. NULL when the actor is no longer a Member (e.g. a `member_left` row outlives the Member row's deletion). See FK note below. |
| `kind` | `TEXT` | NO | — | App-layer-enforced enum: `pick_added` \| `pick_removed` \| `member_joined` \| `member_left` \| `group_created`. |
| `payload` | `JSONB` | NO | `'{}'` | Kind-specific context. Shapes documented in § 4.27. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | Audit + sort key. |

Indexes:

- PK `(id)`.
- `idx_group_activity_group_time (group_id, created_at DESC)` — primary read path; "show the last N events in this group."

FKs: `group_id → group(id)` ON DELETE CASCADE; `member_id → member(id)` **ON DELETE SET NULL** (preserves the historical row when a Member leaves; the `member_left` row's `payload` carries the display name for screen-render).

Pruning: a future cron sweep deletes rows older than 90 days OR keeps the latest 500 rows per group, whichever bound triggers first (§ 4.27). v1 doesn't ship the sweep; rows accumulate until the cron daemon lands.

---

## 3. Index inventory (day-1)

| Index | Table | Justifying query |
|---|---|---|
| `uq_user_username (username) WHERE username IS NOT NULL` | user | Login by username for `local`-auth users; partial because SSO users have NULL username. |
| `uq_user_email (email) WHERE email IS NOT NULL` | user | Email uniqueness for signup; future password reset; SSO users with private-relay emails fit the same constraint. |
| `uq_user_apple_subject (apple_subject_id) WHERE apple_subject_id IS NOT NULL` | user | One-User-per-Apple-identity. Lookup path for `/api/auth/apple`. |
| `uq_user_google_subject (google_subject_id) WHERE google_subject_id IS NOT NULL` | user | One-User-per-Google-identity. Lookup path for `/api/auth/google`. |
| `uq_group_invite_code (invite_code)` | group | URL → group resolution at every group-scoped endpoint. |
| `idx_group_archive_sweep (last_active_at) WHERE archived_at IS NULL` | group | Nightly archival sweep. |
| `idx_group_event (event_id)` | group | "List groups for event X" admin queries. |
| `uq_member_user_group (user_id, group_id)` | member | One Member per (User, Group). |
| `idx_member_group (group_id)` | member | Top-bar member avatars. |
| `idx_member_user (user_id)` | member | `GET /api/users/me/groups`. |
| `uq_device_user_token (user_id, push_token)` | device | One device-token per user (idempotent re-register). |
| `idx_device_user_active (user_id) WHERE revoked_at IS NULL` | device | "Send push to user's active devices." |
| `uq_event_external (source_adapter, external_id) WHERE external_id IS NOT NULL` | event | Re-import idempotency. |
| `uq_stage_external (event_id, external_id)` | stage | Re-import match. |
| `idx_stage_event_order (event_id, display_order)` | stage | Stage-column ordering. |
| `uq_set_external (event_id, external_id)` | set | Re-import match. |
| `idx_set_event_starts (event_id, starts_at)` | set | Full lineup ordered by time. |
| `idx_set_stage_starts (stage_id, starts_at)` | set | Stage-filtered calendar view. |
| `uq_artist_name_normalized (name_normalized)` | artist | Dedup on import. |
| `idx_artist_spotify (spotify_artist_id) WHERE spotify_artist_id IS NOT NULL` | artist | "Find artist by Spotify ID" used by enrichment + cache backfill. |
| `uq_artist_source_ext (source_adapter, external_id)` | artist_source_ref | Cross-source uniqueness. |
| `idx_setartist_artist (artist_id)` | set_artist | "All sets featuring artist X." |
| `idx_pick_set_active (set_id) WHERE state = 'active'` | pick | Per-set dot rendering. |
| `idx_pick_member_active (member_id) WHERE state = 'active'` | pick | "My picks" view. |
| `idx_artist_cache_fetched (fetched_at) WHERE fetched_at IS NOT NULL` | artist_cache | TTL refresh sweep. |
| `idx_group_activity_group_time (group_id, created_at DESC)` | group_activity | "Last N events in this group" feed render. |

### 3.1 Justifying queries — full SQL

**Q1 — All active picks for a group, with display info** (powers `GET /api/groups/{invite_code}` and per-set dots).

```sql
SELECT p.member_id, p.set_id, p.state, p.state_clock_ms,
       m.user_id,
       COALESCE(m.display_name_override, u.display_name, u.username) AS display_name,
       u.avatar_color
FROM   member m
JOIN   "user"  u ON u.id = m.user_id
JOIN   pick    p ON p.member_id = m.id
WHERE  m.group_id = $1               -- uses idx_member_group
  AND  p.state    = 'active';        -- uses idx_pick_member_active (partial)
```

Plan: idx_member_group for members → PK lookup on user (for display fields) → idx_pick_member_active for active picks. No table scans.

**Q2 — Snapshot for "where will the group be at time T"** (powers `GET /api/groups/{invite_code}/snapshot`; § 4.13). The group implies the event (§ 4.25); no `event_id` query param needed.

```sql
WITH window_sets AS (
    SELECT s.set_id, s.stage_id, s.display_name, s.day_label,
           s.starts_at, s.ends_at
    FROM   set s
    WHERE  s.event_id  = (SELECT event_id FROM "group" WHERE id = $group_id)
      AND  s.starts_at <  $at + ($window_minutes * interval '1 minute')
      AND  s.ends_at   >  $at
)
SELECT ws.*,
       st.name AS stage_name,
       st.display_order,
       p.member_id,
       m.user_id,
       COALESCE(m.display_name_override, u.display_name, u.username) AS display_name,
       u.avatar_color
FROM   window_sets ws
JOIN   stage   st ON st.stage_id  = ws.stage_id
LEFT JOIN pick p  ON p.set_id     = ws.set_id
                 AND p.state      = 'active'  -- uses idx_pick_set_active (partial)
LEFT JOIN member m ON m.id        = p.member_id
                  AND m.group_id  = $group_id
LEFT JOIN "user" u ON u.id        = m.user_id
ORDER BY st.display_order, ws.starts_at;
```

Plan: subquery resolves event_id from group → idx_set_event_starts range scan → stage PK → idx_pick_set_active partial → member PK → user PK.

**Q3 — User's groups list** (powers `GET /api/users/me/groups`).

```sql
SELECT g.id, g.name, g.invite_code, g.event_id, g.created_by_user_id,
       g.last_active_at, g.archived_at, m.id AS member_id, m.joined_at
FROM   member m
JOIN   "group" g ON g.id = m.group_id
WHERE  m.user_id = $1                 -- uses idx_member_user
ORDER BY g.last_active_at DESC;
```

**Q4 — Login by username (local-auth users only).**

```sql
SELECT * FROM "user"
WHERE auth_provider = 'local'
  AND LOWER(username) = LOWER($1);  -- uses uq_user_username (partial)
```

The DB index is partial `UNIQUE(username) WHERE username IS NOT NULL`; correctness depends on the app always writing lowercased values (§ 4.16). Login compares with `LOWER()` on both sides as defence-in-depth. SSO users sign in via `/api/auth/apple` (§ 4.20) or `/api/auth/google` (§ 4.24).

**Q5 — Apple Sign-In match.**

```sql
SELECT * FROM "user"
WHERE auth_provider = 'apple'
  AND apple_subject_id = $1;       -- uses uq_user_apple_subject (partial)
```

Run after the server validates Apple's identity token against Apple's JWKS and extracts the `sub` claim. No match → create new User with `auth_provider = 'apple'`; match → reuse the existing row.

**Q6 — Google Sign-In match.**

```sql
SELECT * FROM "user"
WHERE auth_provider = 'google'
  AND google_subject_id = $1;      -- uses uq_user_google_subject (partial)
```

Same shape as Q5. Run after the server validates Google's ID token against Google's JWKS and extracts the `sub` claim.

**Q7 — Recent activity feed for a group.**

```sql
SELECT id, member_id, kind, payload, created_at
FROM   group_activity
WHERE  group_id = $1                  -- uses idx_group_activity_group_time
ORDER BY created_at DESC
LIMIT $2;
```

---

## 4. Design decisions log

Each decision: chosen option · reasoning · alternative considered · why rejected.

### 4.1 Primary keys — UUIDv7 across the board

**Chosen.** UUIDv7 (RFC 9562) for `user`, `group`, `member`, `device`, `event`, `stage`, `set`, `artist`, `group_activity`. `artist_cache` keys on `name_normalized` (decoupled from the registry per [ADR-005](ADR-005-music-data-source.md)).

Reasoning:

- **Time-ordered sortability** — leading 48-bit ms timestamp clusters index inserts temporally. Matters as `set`, `pick`, and `group_activity` grow.
- **No information disclosure** — sequential integer ids would leak counts; UUIDs don't.
- **Forward-compat with horizontal scale** — UUIDs are globally unique without a coordinator.

Alternative — **autoincrement BIGINT**: rejected. Information leak via API responses; horizontal-scale headaches later.

Alternative — **ULID**: rejected. Functionally similar; UUIDv7 has stronger Python ecosystem support and is an IETF standard.

### 4.2 Time zones — `TIMESTAMPTZ` + `event.timezone`

**Chosen.** Store all timestamps as `TIMESTAMPTZ`. Store `event.timezone` as IANA name. Denormalize `set.day_label` from source.

Reasoning:

- `TIMESTAMPTZ` preserves the absolute instant; no DST ambiguity.
- `event.timezone` enables correct day boundaries on the FE.
- `set.day_label` keeps the source's day rollover semantics intact without re-derivation. Verified against 27 midnight-straddling rows in the TML fixture.
- The source's `+1s` end-time quirk is stored verbatim.

### 4.3 Artist deduplication — `name_normalized` with unique index

**Chosen.** `artist.name_normalized = lower(NFKD(strip_diacritics(name))).strip()` with whitespace collapsed.

Same approach is **not** applied to `user.username` — usernames are stored lowercased only (no diacritic strip), because allowing accented usernames in distinct accounts is valuable; the lowercase rule is enough to prevent the case-collision bug.

Alternative — fuzzy match for artists: rejected. False positives merge distinct artists.

### 4.4 Set ↔ Artist join — `set_artist` PK `(set_id, artist_id)` + unique `(set_id, position)`

**Chosen** (unchanged). Position = source array order, 0-indexed.

### 4.5 Pick concurrency — LWW with client-assigned `state_clock_ms`

**Chosen** (unchanged). Client sends `state_clock_ms` (Unix epoch ms). Server accepts if newer; tie-break by server receive order. The server enforces that `current_user` owns the Member identified — picks-on-behalf-of is impossible.

### 4.6 Soft delete on Pick — tombstone

**Chosen** (unchanged). `state` flips between `active` and `tombstoned`; `state_clock_ms` updates on every transition. Preserves LWW correctness across out-of-order syncs.

> Distinguish from Member: Member uses **hard delete** (§ 4.28). Pick within a still-Member relationship uses tombstone. When a Member is deleted, tombstone-or-active distinctions on their picks are moot — the whole row cascades.

### 4.7 Indexes — see § 3

### 4.8 External-id collisions — `(source_adapter, external_id)`; multi-source artists via `artist_source_ref`

**Chosen** (unchanged).

### 4.9 Migration ordering — everything in V001 baseline

**Chosen.** All **13 tables** land in V001. Zero users at this point — clean slate.

### 4.10 Wire shape — Pydantic v2, snake_case, mirrored from the table layer

**Chosen.** See [`docs/schemas/reference/v1_pydantic.py`](../schemas/reference/v1_pydantic.py). Request and response shapes split per endpoint. snake_case end-to-end per [CLAUDE.md](../../CLAUDE.md).

### 4.11 Invite code = group's `invite_code` column, distinct from `group.id`

**Chosen.** The 8-char Crockford base32 `invite_code` is the URL-facing string (`/g/AB7K9MNP`). `group.id` (UUID) is the internal FK target. No separate `invite_token` table; no expiry; no rotation.

Reasoning:

- **Internal FK target stays UUID** for consistency with the rest of the schema and to avoid having every join carry 8 chars.
- **No expiry** matches the lifecycle ([PRD § 5.1](../PRD.md)): code lives as long as the group does (90 days inactive → archive).
- **No rotation** matches [ADR-003 superseded](ADR-003-auth-model.md) — the link is the credential equivalent for the group. Group creator can create a new group and re-invite if a code leaks.

### 4.12 No per-Member color — `user.avatar_color` is the single source of truth

**Chosen.** Color is on `user`, not on `member`. The friends-list-spec BE-FL-002 ("assign least-used color from a 12-palette at join time") **does not apply** under the new model — a user's color is part of their account identity.

Trade-off: two users in the same group with the same avatar color will look the same. The "12 distinct colors per group" UX guarantee is broken. Flagged as a [cascade follow-up](ADR-003-auth-model.md) on the friends-list-spec.

### 4.13 Snapshot endpoint — all-member visibility; denormalized for screenshot

**Chosen.** `GET /api/groups/{invite_code}/snapshot?at={iso_time}&window_minutes={int}` returns **every active pick from every Member of the group** within the window, NOT just the calling user's picks. The wire shape denormalizes display names and avatar colors so a single screen capture is intelligible without further lookups.

**No `event_id` query param** — the group is 1:1 with an event (§ 4.25), so the server resolves the event from the group.

Powered by **existing indexes**; no schema change. SQL: Q2 in § 3.1.

Wire shape rules:

- Top-level: `group_name`, `event_name`, `timezone` (IANA), `snapshot_at`, `window_minutes`.
- Per stage: `name`, `display_order`, `sets[]`.
- Per set: `display_name`, `artist_names: list[str]` (denormalized — saves a per-artist lookup), `day_label`, `starts_at`, `ends_at`, `pickers: list[SnapshotMember]`.
- Per picker: `user_id`, `member_id`, `display_name` (resolved via `COALESCE(member.display_name_override, user.display_name, user.username)`), `avatar_color`.

Order: stages by `display_order` ascending; sets within a stage by `starts_at` ascending. Layout-deterministic across captures.

### 4.14 Polling cadence — 15–30s with conditional GETs (Last-Modified)

**Chosen.** The FE polls `GET /api/groups/{invite_code}` at **15s** when the calendar view is foregrounded; the snapshot endpoint `GET /api/groups/{invite_code}/snapshot` is hit on user demand and re-polled at **30s** while the snapshot view stays open. **Both endpoints** return a `Last-Modified` header derived from `MAX(pick.server_last_updated_at, member.joined_at)` for the group. The FE sends `If-Modified-Since`; the server returns **304 Not Modified** with no body when the group state hasn't changed.

Reasoning:

- **15s is fast enough to feel real-time** for the per-set member dots; 30s on the snapshot is fine because the user is staring at a static screen capture they'll share.
- **Conditional GETs save bandwidth** on the festival floor where mobile data is metered/spotty (relevant on native iOS/Android per [ADR-001](ADR-001-tech-stack.md)). Most polls during quiet periods hit 304.
- **Last-Modified over ETag** — simpler. The granularity (server-assigned `TIMESTAMPTZ` to the millisecond on `pick.server_last_updated_at`) is enough. Rare same-ms churn falls back to a 200 with the fresh payload.

Alternative — **WebSockets**: deferred to v2 per [ARCHITECTURE.md § Real-time strategy](../ARCHITECTURE.md). Polling first, WS only if user reports indicate polling lag.

### 4.15 Member re-join — fresh Member row + fresh picks

**Chosen.** Because Leave hard-deletes (§ 4.28), re-joining after a Leave creates a **new** Member row with a new `id`. The `(user_id, group_id)` UNIQUE constraint guarantees the previous row is gone before the new one inserts. The previous picks cascaded with the old Member; the rejoined member starts with zero picks.

Reasoning:

- Hard delete is the load-bearing choice (§ 4.28); rejoin behaviour follows.
- Simple mental model: "I left, my picks are gone, when I come back I start fresh."
- No "ghost" picks from a previous membership clouding the new one.

### 4.16 Username — lowercase store + lowercase compare (`local` auth_provider only)

**Chosen.** Application code lowercases on every username write (signup, `PATCH /api/users/me`). Login + lookup compare with `LOWER() = LOWER()` on both sides as defence-in-depth. Database `UNIQUE(username) WHERE username IS NOT NULL` is partial; correctness depends on the app's lowercase invariant. SSO-provider users (`auth_provider != 'local'`) have NULL username — they don't go through this query path.

Reasoning:

- Eliminates the "Jerome signs up, jerome can't log in" bug class. A reasonable engineer's lesson worth not relearning.
- Username uniqueness is also case-insensitive — `Jerome` and `jerome` are the same identity.
- Email follows the same rule (stored lowercased; lookup `LOWER() = LOWER()`).

### 4.17 Password hashing — argon2id (m=64 MiB, t=3, p=4)

**Chosen.** Argon2id with parameters approximating OWASP's current recommendation (post-2024 guidance): memory cost `m = 65536 KiB` (64 MiB), time cost `t = 3` iterations, parallelism `p = 4`. Stored as the full encoded string (`$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>`) so future param tuning is per-row.

Library: `argon2-cffi` (Python).

### 4.18 Email — optional in v1; no password-reset flow

**Chosen.** `user.email` is `NULL`-able. `local` signup doesn't require it. No password-reset endpoint in v1; "I forgot my password" is a manual support case.

Apple/Google-auth caveat: both providers return an email on first authentication. Apple may return a private-relay address (`*@privaterelay.appleid.com`); we store whatever the provider returns verbatim. Subsequent sign-ins match on `apple_subject_id` / `google_subject_id`, not email, so a user toggling email visibility doesn't fork into two accounts.

### 4.19 JWT — HS256, 24h access + 7d refresh, no v1 revocation

**Chosen.** HS256 signed with `JWT_SECRET` env var. Access token 24h, refresh token 7d. Refresh-token revocation deferred to v2 (the `jti` claim is included now so a v2 revocation table can land additively).

### 4.20 Apple Sign-In — v1 (locked)

**Chosen (locked 2026-06-18).** Sign In with Apple is implemented in V001 with the schema columns from § 2.1 (`auth_provider = 'apple'`, `apple_subject_id`).

**Reasoning — Apple's App Store policy:**

- Per Apple's [App Review Guideline 4.8](https://developer.apple.com/app-store/review/guidelines/#sign-in-with-apple), apps on iOS that offer any third-party social login (including Google) **must** also offer Sign In with Apple. With Google Sign-In also v1 (§ 4.24), Apple is not optional.

**Flow (native client via `expo-apple-authentication`):**

1. Native app invokes Apple's `ASAuthorizationAppleIDProvider` (iOS).
2. Apple returns an identity token (JWT signed by Apple) + optionally `full_name` and `email` (only on first sign-in for a given app).
3. App POSTs to `POST /api/auth/apple` with `{identity_token, display_name?, email?}`.
4. Server fetches Apple's JWKS (cached), validates the token's signature + `aud` (our app's bundle id) + `iss` (`https://appleid.apple.com`) + `exp`.
5. Server extracts `sub` (Apple's stable user id), runs Q5 (§ 3.1) — match or create User.
6. Server returns `AuthResponse` (user + JWT pair, same shape as `/auth/login`).

**Identity merging is not in scope** — a user who signs up with Apple then later wants to "link" a `local` username/password is told "create a new account or contact support." A merge flow needs a separate ADR.

### 4.21 Display name — stored as-typed (preserve emojis + case)

**Chosen.** `user.display_name`, `member.display_name_override`, and `group.name` are stored verbatim — emojis preserved, casing preserved, leading/trailing whitespace stripped, internal whitespace untouched. The FE renders them as-typed.

Length: 1–80 graphemes.

Username (`local` auth_provider) is separately constrained to `[a-z0-9_-]{3,32}` (§ 4.16).

### 4.22 Invite code — 8-char Crockford base32 (confirmed)

**Chosen.** `group.invite_code` is 8 characters from the Crockford base32 alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ` — no `I`, `L`, `O`, `U`). Server normalizes on read: uppercase input + map `i`→`1`, `l`→`1`, `o`→`0` (Crockford's canonical decode map).

### 4.23 Native-mobile client locked

**Chosen (locked 2026-06-18).** React Native + Expo per [ADR-001](ADR-001-tech-stack.md). `expo-sqlite` + AsyncStorage per [ADR-004](ADR-004-offline-strategy.md). The data schema in this ADR remains platform-agnostic; the LWW algorithm (§ 4.5) is independent of client storage.

### 4.24 Google Sign-In — v1 (locked)

**Chosen (locked 2026-06-18).** Google Sign-In is implemented in V001 with the schema columns from § 2.1 (`auth_provider = 'google'`, `google_subject_id`).

**Reasoning:**

- **Both iPhone and Android ship v1** — Google is table-stakes on Android. Without it, Android users land on username/password and bounce (the Android equivalent of iOS's Apple-Sign-In expectation).
- **Apple Guideline 4.8 implication** — once Google is on the iOS build, Apple is mandatory (and it's already in V001 per § 4.20).
- **Schema symmetry** with Apple — `google_subject_id` mirrors `apple_subject_id`; the `auth_provider` enum is symmetric across the three values.

**Flow (native client via `expo-auth-session` / Google's native SDK):**

1. Native app invokes Google's auth flow.
2. Google returns an ID token (JWT signed by Google).
3. App POSTs to `POST /api/auth/google` with `{id_token, display_name?, email?}`.
4. Server fetches Google's JWKS (`https://www.googleapis.com/oauth2/v3/certs`, cached), validates the token's signature + `aud` (our app's Google client id) + `iss` (`https://accounts.google.com`) + `exp`.
5. Server extracts `sub` (Google's stable user id), runs Q6 (§ 3.1) — match or create User.
6. Server returns `AuthResponse` (user + JWT pair, same shape as `/auth/login` and `/auth/apple`).

**Identity merging is not in scope** (same rule as § 4.20).

### 4.25 Group ↔ Event is **one-to-one** (locked)

**Chosen (locked 2026-06-18).** Each Group is scoped to **exactly one** Event. `group.event_id` is a NOT NULL FK to `event`. No `group_event` join table.

Reasoning:

- **UX clarity.** "What festival is this group about?" has a single answer. The calendar view, snapshot view, and pick semantics all key off one event.
- **Forces an up-front choice.** The FE "create group" flow must surface an event picker. Friends who do TML 2026 W2 + EDC Las Vegas 2026 create two groups.
- **Snapshot endpoint signature** stays clean — no `event_id` query param; the group implies it (§ 4.13, § Q2).
- **Cascade semantics are local.** Deleting an Event cascades to its Sets, Stages, AND its Groups — predictable.

Alternative — **many Events per Group** (join table): rejected. The "which event is this calendar showing?" UI lands on an extra picker; the snapshot endpoint grows an `event_id` param; the cross-event semantics of "Sarah picked the same set name at two different festivals" muddy reporting.

Alternative — **nullable event_id with an "unscoped" group**: rejected. Every meaningful action in the group is event-bound; no v1 user need.

### 4.26 Push tokens — `device` table from V001 (locked)

**Chosen (locked 2026-06-18).** The `device` table (§ 2.12) ships in V001 even though v1 does not yet send push notifications.

Reasoning:

- **No future migration.** When push lands (a v1.x ticket), the schema is already in place; the work is app-layer-only (Expo push registration + a send pipeline).
- **Provider abstraction.** `push_provider` enum has `expo` / `apns` / `fcm` from the start. v1 only writes `'expo'` (Expo's service handles both APNs + FCM behind a single token). If we later eject from Expo to bare iOS+Android, the schema already carries the `apns_token` / `fcm_token` lane.
- **Per-device subscription.** A separate `device` table (vs single `expo_push_token` column on `user`) handles multi-device users naturally — Jerome on his phone AND iPad both get the push.
- **Hygiene.** `last_seen_at` + `revoked_at` give the push send pipeline a clean "skip stale tokens, retire bad ones" path.

Alternative — **`user.expo_push_token` column**: rejected. One device per user is wrong (the user has multiple devices).

Alternative — **wait until push is in scope**: rejected. Migration cost is real (the table touches user); landing it now is free.

### 4.27 Group activity log — `group_activity` table from V001 (locked)

**Chosen (locked 2026-06-18).** The `group_activity` table (§ 2.13) ships in V001 and is written by the API on every relevant mutation.

**Kinds + payload shapes** (all JSON):

| Kind | `member_id` | Payload shape |
|---|---|---|
| `group_created` | the creator's member_id | `{group_name, event_id, event_name}` |
| `member_joined` | the joining member_id | `{display_name, avatar_color}` (snapshot at join time) |
| `member_left` | NULL (member row was just deleted) | `{display_name, avatar_color}` (snapshot from the row about to be deleted) |
| `pick_added` | the picker's member_id | `{set_id, set_display_name, stage_name, starts_at, display_name, avatar_color}` |
| `pick_removed` | the picker's member_id | `{set_id, set_display_name, stage_name, display_name, avatar_color}` |

**Pruning rule (forward-compat note — cron daemon out of scope V001).** A future cron sweep deletes `group_activity` rows where:

- `created_at < now() - interval '90 days'`, OR
- the row is older than the most-recent 500 rows for that group.

Whichever bound triggers first. The job lives behind a feature flag; until it runs, rows accumulate. The sweep is safe to run concurrently with writes because `kind`-specific recipients (push notifications, in-app feed) read at most the last few hundred rows.

Reasoning:

- **Drives the in-app feed** — Phase 2-ish "what changed in this group?" view reads from this table.
- **Drives push notifications later** — the push pipeline ingests `group_activity` inserts and notifies the right Device rows.
- **Denormalized payload** — display name + avatar color baked in so render doesn't need to JOIN against `user` (and survives `member_left` after the Member row is gone).

Alternative — **derive from `pick` + `member` history**: rejected. `member` is hard-deleted (§ 4.28); the history isn't recoverable without a log.

Alternative — **defer to v1.x**: rejected. A late-add migration costs a table creation + a backfill of "what happened before today?" — no good answer. Ship it from V001.

### 4.28 Leave group = **hard delete** on Member (locked)

**Chosen (locked 2026-06-18).** Leaving a group hard-deletes the Member row. `pick.member_id → member(id)` is `ON DELETE CASCADE`, so the User's picks for that group are deleted with the Member row. **`member.left_at` is removed from the schema** (the pre-pivot soft-delete column is gone).

**Forward-compat acceptance criterion (FE):** The Leave action MUST show a confirmation dialog before invoking the destructive endpoint. Suggested copy: **"Leave group? Your picks will be deleted."** The dialog is a load-bearing safety net; this ADR encodes it so the FE ticket cannot ship without it.

Reasoning:

- **Simple mental model.** "I left, I'm gone." No "soft-left ghost" rows polluting `(user_id, group_id)` uniqueness checks.
- **Privacy.** Picks are a fingerprint of where the user planned to be. After Leave they shouldn't survive on the server.
- **Storage hygiene.** Activity log (§ 4.27) captures the `member_left` event with a denormalized snapshot, so the historical record exists without keeping the Member row.

Alternative — **soft delete via `left_at`** (the pre-pivot design): rejected. Soft-delete added partial indexes and a "rejoin reactivates" rule (§ pre-pivot 4.15); both are gone now. Picks-survive-Leave was the worst part of soft-delete.

Alternative — **delete Member, retain Picks** (orphan picks with NULL member_id): rejected. Orphan picks have no display name to render and no User to attribute to. Worse than just deleting them.

### 4.29 Artist upsert on lineup import — trust latest non-null Spotify ID (locked)

**Chosen (locked 2026-06-18).** Lineup re-import upserts artists keyed on `name_normalized`. The upsert algorithm:

```
For each artist in the incoming payload:
  normalized = normalize(payload.name)
  existing = SELECT * FROM artist WHERE name_normalized = normalized
  if existing is NULL:
    INSERT new artist with payload values (name, name_normalized, spotify_artist_id, image_url, social_links).
  else:
    UPDATE existing artist:
      - name: keep existing (first-import wins on the canonical display name; § 4.3).
      - name_normalized: unchanged.
      - spotify_artist_id:
          if payload.spotify_artist_id IS NOT NULL:
            overwrite with payload value     # trust the latest
          else:
            keep existing value              # don't lose what we already have
      - image_url:
          if payload.image_url IS NOT NULL:
            overwrite with payload value     # trust the latest
          else:
            keep existing value
      - social_links:
          merge payload values into existing JSON, preferring payload's non-null fields.
```

Reasoning:

- **Sources upgrade.** Festival lineup APIs add a Spotify link to an artist mid-cycle. We want the next re-import to pick that up.
- **Sources also regress.** A subsequent payload may omit the Spotify ID (different scraper, transient outage). Replacing a known good ID with NULL would be a regression. Hence the asymmetry: overwrite on non-null, keep on null.
- **`spotify_artist_id` on `artist`** (vs only in `artist_cache`) gives the lineup import a direct write path — no detour through the cache table — and lets queries like "all sets featuring Spotify ID X" use an indexed column.

Alternative — **always overwrite (including with NULL)**: rejected. Loses good data on a regressed payload.

Alternative — **only set on first import (insert-only)**: rejected. We never pick up updates from the source.

Alternative — **leave the Spotify ID solely in `artist_cache`**: rejected. The cache is keyed on `name_normalized` (decoupled per [ADR-005](ADR-005-music-data-source.md)) but is meant for Spotify/Last.fm enrichment; lineup-payload IDs are first-class metadata about the registry itself.

---

## 5. Open questions

> Five product decisions ratified 2026-06-18 collapsed open questions § 5.6, § 5.8, § 5.2 (ADR-004 + ADR-001 parts) from the previous revision. The remaining open questions are:

### 5.1 PRD alignment — when?

This ADR contradicts [PRD § 1, § 2, § 4](../PRD.md). **Confirm:** OK to merge ADR-006 first and update PRD in a follow-up, or block this PR on the PRD update landing first?

### 5.2 friends-list-spec follow-up

**[friends-list-spec BE-FL-002](../features/friends-list-spec.md)** ("least-used color from the 12-palette at join time") is dead — color lives on User (§ 4.12). **Confirm:** follow-up PR removes BE-FL-002 and updates the per-set-dots story?

(ADR-004 + ADR-001 parts of the original § 5.2 are resolved by the supersessions landing in this PR.)

### 5.3 Client clock skew tolerance

Picks LWW on `state_clock_ms` (§ 4.5). Options:

- (A) Accept — document as known limit.
- (B) Reject `state_clock_ms` more than 1 hour ahead of server clock.
- (C) Clamp to `min(client_clock, server_now + buffer)`.

**Recommendation: (B), rejection.**

### 5.4 Lineup import audit row

A `lineup_import` audit row (when, by whom, summary counts) would help admin debugging. Not in V001. **Confirm:** defer to additive migration?

### 5.5 Member color UX regression — fix or accept?

Per § 4.12, two users in the same group with the same `avatar_color` will look identical. Options:

- (A) Accept — color is part of identity; collisions are rare in small groups.
- (B) Override at Member level — add `member.color_hex` (nullable; fallback to user). Resurrects the per-group palette assignment.
- (C) Tiebreak at render time on the FE — collision detection + adjacent-color shift.

**Recommendation: (A) for v1**; can promote to (B) additively if user feedback indicates the regression hurts.

### 5.6 Cross-project memory references

The earlier pivot brief referenced sibling-project memory files (e.g. `feedback_be_snake_case_json`) for the lowercase-username and snake-case-JSON rules. Those files aren't in this project; re-documented the rules in plain language here (§ 4.16) and in [CLAUDE.md § API Conventions](../../CLAUDE.md). **Confirm:** OK to treat any future sibling-project lessons the same way — document them in setlist-picker's own files rather than reference paths in another repo?

---

## 6. Migration plan — V001 baseline

V001 creates **13 tables**. Alembic migration order (FK dependencies):

1. `user`
2. `event`
3. `group` (FK → event, user)
4. `member` (FK → user, group)
5. `device` (FK → user)
6. `stage` (FK → event)
7. `set` (FK → event, stage)
8. `artist`
9. `artist_source_ref` (FK → artist)
10. `set_artist` (FK → set, artist)
11. `pick` (FK → member, set)
12. `artist_cache`
13. `group_activity` (FK → group, member SET NULL)

Then all indexes from § 3.

**Migration is out of scope for this PR.** The Phase 1 ticket reads this ADR and writes V001.

> Per [CLAUDE.md](../../CLAUDE.md), `ls services/api/alembic/versions/ | tail -5` before generating. V001 will be the first.

---

## 7. References

- [PRD.md](../PRD.md) — NB: § 1, § 2, § 4 still encode the pre-pivot anonymous model; follow-up PR required (§ 5.1).
- [ARCHITECTURE.md § Data model](../ARCHITECTURE.md) — slim summary pointing here; § Auth model + § Stack updated by this PR.
- [ADR-001 — Tech stack](ADR-001-tech-stack.md) — Postgres-from-start + RN/Expo locked in 2026-06-18.
- [ADR-003 — Auth model (superseded)](ADR-003-auth-model.md) — historical context preserved.
- [ADR-004 — Offline strategy](ADR-004-offline-strategy.md) — `expo-sqlite` + AsyncStorage locked in 2026-06-18.
- [ADR-005 — Music data source](ADR-005-music-data-source.md) — artist_cache shape, fallback chain.
- [features/calendar-spec.md](../features/calendar-spec.md)
- [features/friends-list-spec.md](../features/friends-list-spec.md) — BE-FL-002 deprecated by § 4.12; follow-up required (§ 5.2).
- [features/artist-drilldown-spec.md](../features/artist-drilldown-spec.md)
- [`docs/schemas/reference/v1_pydantic.py`](../schemas/reference/v1_pydantic.py) — Pydantic v2 reference shapes including auth flows.
- [`.local-data/tml26-w2.json`](../../.local-data/tml26-w2.json) — round-trip fixture (gitignored).
