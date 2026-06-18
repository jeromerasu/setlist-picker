# ADR-006: Initial data schema + auth model (V001 baseline)

## Status
**Proposed.** Pending sign-off from Jerome on the design-decisions log (§ 5).

This ADR **supersedes [ADR-003](ADR-003-auth-model.md)**: the v1 product now ships with authenticated user accounts (username + password + JWT), not anonymous per-device members.

> **PRD alignment required** — the current [PRD § 1, § 2, § 4](../PRD.md) commits to "no account, no email, no signup, under 30 seconds from invite to first pick." That language predates this pivot. **Sign-off on this ADR implies a follow-up PR to align the PRD** (and propagate to ADR-004 § Consequences and friends-list-spec § Member colors — both still encode anonymous-device assumptions). The PRD update is **out of scope for this PR** to keep the diff focused on schema + auth design.

## Context

Phase 1 of the [ROADMAP](../ROADMAP.md) creates the FastAPI skeleton and the first Alembic migration. Every backend ticket — auth, group lifecycle, pick sync, lineup import, artist drill-down, screenshot snapshot — depends on the V001 schema landing first.

The pivot from ADR-003's anonymous model is driven by:

- **Cross-device sync.** ADR-003's "phone and laptop joining as Jerome are two distinct presences" worked for v1 anonymity but breaks the core "where is everyone right now?" promise when one user's picks split across devices.
- **Screenshot-share UX.** The snapshot endpoint (§ 4.13) returns a per-stage view annotated with picker names; resolving stable identities improves the screenshot's value when shared.
- **Real-ish-time visibility into the whole group's pick history** — Jerome confirmed in the 2026-06-18 product clarification that picks are server-authoritative, every member can read every other member's picks, and the server is the source of truth for groups + members + picks.

This ADR must support:

- Authenticated user identity (username + password AND Apple Sign-In; JWT-based session) — § Auth model below.
- Group lifecycle with an invite code distinct from the internal group id ([calendar-spec](../features/calendar-spec.md), [friends-list-spec](../features/friends-list-spec.md)).
- Per-set member picks with last-write-wins reconciliation ([ADR-004](ADR-004-offline-strategy.md)).
- Artist drill-down with cache + fallback chain ([ADR-005](ADR-005-music-data-source.md)).
- Lossless round-trip of the source lineup JSON under the adapter pattern — verified against [`.local-data/tml26-w2.json`](../../.local-data/tml26-w2.json) (405 performances, 15 stages, 420 artists, 35 b2b sets, 27 sets straddling midnight, 73 sets whose display name differs from the headlining artist name).

### Mobile-native direction (2026-06-18 update)

Jerome flagged that v1 will likely ship as a native mobile app rather than a PWA. **The data schema in this ADR is platform-agnostic and does not change.** What does change (encoded in this PR):

- Apple Sign-In becomes a likely v1 requirement (App Store Guideline 4.8) — schema columns + flow in § 4.20.
- The offline client-side store on mobile is SQLite/AsyncStorage, not IndexedDB — § 4.23. The Pick LWW algorithm (§ 4.5) is unchanged.
- Push notifications become an option later — forward-compat note in § 5.8 (no V001 column).
- Display name handling on mobile keyboards (emoji + case) — § 4.21.
- Invite code UX via Share Sheet — § 4.22 confirms 8-char Crockford base32.

**ADR-001 (Tech stack) revision is OUT OF SCOPE for this PR** — Jerome will spawn it separately when the RN/Expo vs Flutter vs native call lands.

### Canonical UX flow (post-pivot)

1. New visitor → signup with `{username, password, email?, display_name?}`. Returns user + access/refresh JWT pair.
2. Returning visitor → login with `{username, password}`. Returns user + JWT pair.
3. Authenticated user creates a group → server returns the new group + the 8-char Crockford base32 invite code + auto-creates the creator's Member row.
4. Authenticated user shares the invite code out-of-band.
5. Authenticated friend joins via `POST /api/groups/join` with `{invite_code, display_name_override?}` → server creates a Member row scoped to that User + Group, or returns the existing Member if the user already joined.
6. Each User sees `GET /api/users/me/groups` — every group the user is a Member of, sourced server-side (not localStorage). Token-authed; no client-side roster.
7. Inside a group: festival calendar with per-set picker dots. Picks server-authoritative, polled by the FE; cross-device sync is automatic because picks are scoped to Member (= User × Group), not to device.
8. Tap an artist → drill-down ([ADR-005](ADR-005-music-data-source.md)).
9. Pick = "I'm going to this set." Public within the group (§ 4.12).
10. **Screenshotable "where will we be at time T" view** — the snapshot endpoint (§ 4.13) returns picks from **all** group members with display names + avatar colors denormalized for self-contained screen captures.

The [ARCHITECTURE.md § Data model](../ARCHITECTURE.md) block has been slim-summarized; this ADR is the authoritative source from here forward.

---

## 1. Auth model

### 1.1 Identity

- **User** is the account of record (§ 2.1). One human → one User → potentially many Members (one per Group).
- **Member** is the per-Group join row (§ 2.3). Owns the picks via FK. Optionally carries a per-group display-name override.
- **Group** owns the invite code that propagates new Members (§ 2.2).

### 1.2 Credentials

- **Username** — required at signup, unique. Stored lowercased; comparisons run `LOWER() = LOWER()` on both sides. Eliminates the classic "Jerome registered, jerome login fails" bug class (a reasonable engineer's lesson; documented here so it doesn't repeat). § 4.16.
- **Password** — argon2id hash. § 4.17.
- **Email** — optional in v1. Without email there's no password-reset flow; users who forget their password contact support (manual reset). § 4.18.

### 1.3 Session

- **JWT** (HS256, secret in env var `JWT_SECRET`).
- **Access token** — 24h lifetime. Claims: `sub` = `user.id` (string), `iat`, `exp`, `type: "access"`.
- **Refresh token** — 7d lifetime. Claims: `sub`, `iat`, `exp`, `type: "refresh"`, `jti` (refresh-token id for v2 revocation).
- `POST /api/auth/refresh` exchanges a valid refresh token for a new access+refresh pair. v1 does **not** track refresh-token revocation (no `refresh_token` table) — flagged in § 5.

### 1.4 Middleware

- Every endpoint except `POST /api/auth/{signup,login,refresh}` requires a valid access token in `Authorization: Bearer <token>`.
- FastAPI dependency `current_user: User` decodes the JWT, looks up the User by `sub`, returns the row (404 / 401 on failure).
- **Group-scoped endpoints** additionally check that `current_user` has an active Member row for the group (via `(user_id, group_id) WHERE left_at IS NULL`). On miss → 403.
- Picks: the request body does **not** carry a `member_id`. The server derives it from `(current_user.id, group_id)`. Prevents one user posting picks on another's behalf.

### 1.5 Forward compat

- **SSO** (Apple, Google) — see open question § 5.6.
- **Refresh-token revocation** — additive `refresh_token` table later; current `jti` claim makes it possible without a JWT schema change.
- **Email-based password reset** — v2; would require SMTP integration and a `password_reset_token` table.

---

## 2. Tables (V001)

V001 ships 11 tables: `user`, `group`, `member`, `event`, `stage`, `set`, `artist`, `artist_source_ref`, `set_artist`, `pick`, `artist_cache`. Sections below cover `user`, `group`, `member`, `pick` (changed from the pre-pivot draft) and `artist`, `artist_source_ref`, `set_artist`, `artist_cache`, `event`, `stage`, `set` (unchanged from the pre-pivot draft).

Conventions:

- **Primary keys** are UUIDv7 (16-byte binary in Postgres, TEXT in SQLite). Rationale: § 4.1.
- **Timestamps with timezone** are `TIMESTAMPTZ` (Postgres) / ISO-8601 with offset (SQLite via `DateTime(timezone=True)`).
- **JSON columns** are `JSONB` (Postgres) / `JSON` (SQLite). SQLAlchemy's `JSON()` type handles both.
- **`source_adapter`** identifies a lineup adapter, e.g. `event_api_v1`, `manual`.

### 2.1 `user` (NEW)

The account of record. Server-authoritative identity; survives device wipes.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `id` | `UUID` | NO | (UUIDv7) | § 4.1. |
| `auth_provider` | `TEXT` | NO | `'local'` | Enum: `local` \| `apple` \| `google`. Identifies the signup path. `google` is reserved (not implemented in v1). App-layer-enforced enum; SQLite has no native enum. § 4.20. |
| `username` | `TEXT` | YES | NULL | Stored lowercased; the comparison key on login for `local` users. Length 3–32, [a-z0-9_-] only. NULL for SSO-provider users (they sign in via the provider, not by username). § 4.16. |
| `email` | `TEXT` | YES | NULL | Stored lowercased when present. Optional for `local` users (§ 4.18). Apple may return a private-relay address (`*@privaterelay.appleid.com`); we store it verbatim and treat it the same. |
| `password_hash` | `TEXT` | YES | NULL | Argon2id-encoded string. Required for `local`; NULL for SSO. § 4.17. |
| `apple_subject_id` | `TEXT` | YES | NULL | Apple's stable identifier from the Sign In with Apple identity token's `sub` claim. NULL unless `auth_provider = 'apple'`. § 4.20. |
| `display_name` | `TEXT` | YES | NULL | UI-facing name. Falls back to `username` when null. Stored as-typed — emojis and casing preserved (§ 4.21). |
| `avatar_color` | `CHAR(7)` | NO | — | `#RRGGBB`. Picked at signup from a default palette; user can change. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | Updated by app code on any User mutation. |
| `last_login_at` | `TIMESTAMPTZ` | YES | NULL | Updated by `/auth/login` or `/auth/apple`. |

App-layer invariants (no DB CHECK constraints — kept portable across SQLite/Postgres):

- `auth_provider = 'local'` ⇒ `username IS NOT NULL` AND `password_hash IS NOT NULL` AND `apple_subject_id IS NULL`.
- `auth_provider = 'apple'` ⇒ `apple_subject_id IS NOT NULL` AND `password_hash IS NULL`.
- `auth_provider = 'google'` ⇒ reserved; not used in v1.

Indexes:

- PK `(id)`.
- `uq_user_username (username) WHERE username IS NOT NULL` — partial unique; case-insensitive **at the application layer** because we store lowercased (§ 4.16).
- `uq_user_email (email) WHERE email IS NOT NULL` — partial unique.
- `uq_user_apple_subject (apple_subject_id) WHERE apple_subject_id IS NOT NULL` — partial unique. The Apple `sub` claim is globally unique within Apple's identity system; this index matches one User to one Apple identity.

FKs: none.

Example rows:

```text
-- local-auth user
id                 | 0192d6f0-...-0a01
auth_provider      | local
username           | jerome
email              | jerome@example.com
password_hash      | $argon2id$v=19$m=65536,t=3,p=4$...
apple_subject_id   | NULL
display_name       | Jerome 🎶
avatar_color       | #4F46E5
created_at         | 2026-07-20T18:20:00+00:00
updated_at         | 2026-07-25T14:01:33+00:00
last_login_at      | 2026-07-25T14:01:33+00:00

-- apple-auth user (first sign-in)
id                 | 0192d6f0-...-0a02
auth_provider      | apple
username           | NULL
email              | abc123@privaterelay.appleid.com
password_hash      | NULL
apple_subject_id   | 001234.abc...xyz.4321
display_name       | Sarah
avatar_color       | #DC2626
created_at         | 2026-07-20T18:21:11+00:00
updated_at         | 2026-07-20T18:21:11+00:00
last_login_at      | 2026-07-20T18:21:11+00:00
```

### 2.2 `group` (REFACTORED — now UUID PK + separate invite_code)

The shared coordination unit. Now owned by a creator User.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `id` | `UUID` | NO | (UUIDv7) | § 4.1. Internal identifier; replaces the prior `group_code` PK. |
| `name` | `TEXT` | NO | `'Friends 🎵'` | Group's display name. |
| `invite_code` | `CHAR(8)` | NO | (assigned) | 8-char Crockford base32 ([PRD § 5.1](../PRD.md)); the URL-facing code (`/g/AB7K9MNP`). The invite IS the code — § 4.11. |
| `event_id` | `UUID` | NO | — | One group ↔ one event in v1. |
| `created_by_user_id` | `UUID` | NO | — | Creator User. Useful for "you created this group" UI and future creator-only mutations. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | Group creation. |
| `last_active_at` | `TIMESTAMPTZ` | NO | `now()` | Updated on any group write. Drives 90-day archival sweep. |
| `archived_at` | `TIMESTAMPTZ` | YES | NULL | NULL = active. |

Indexes:

- PK `(id)`.
- `uq_group_invite_code (invite_code)` — unique; the URL → group resolution.
- `idx_group_archive_sweep (last_active_at) WHERE archived_at IS NULL` — partial; archival sweep.

FKs: `event_id → event(event_id)`; `created_by_user_id → user(id)`.

Example row:

```text
id                  | 0192d6f8-...-7b3a
name                | Friends 🎵
invite_code         | AB7K9MNP
event_id            | 0192d6f7-...-3c2c
created_by_user_id  | 0192d6f0-...-0a01
created_at          | 2026-07-20T18:22:09+00:00
last_active_at      | 2026-07-25T14:01:33+00:00
archived_at         | NULL
```

### 2.3 `member` (REFACTORED — now a User × Group join)

A User's membership in a Group. One row per `(user_id, group_id)` pair.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `id` | `UUID` | NO | (UUIDv7) | Surrogate PK so picks have a stable FK target even if (user_id, group_id) is later refactored. |
| `user_id` | `UUID` | NO | — | FK → user. |
| `group_id` | `UUID` | NO | — | FK → group. |
| `display_name_override` | `TEXT` | YES | NULL | Per-group nickname. Falls back to `user.display_name` → `user.username`. Lets "Jerome" be "JR" in one group. |
| `joined_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |
| `left_at` | `TIMESTAMPTZ` | YES | NULL | Soft-remove per [friends-list-spec API contract](../features/friends-list-spec.md). NULL = present. Picks retained for historical context. |

Indexes:

- PK `(id)`.
- `uq_member_user_group (user_id, group_id)` — unique; a User can only be a Member of a Group once. Rejoin after soft-leave re-activates the row (sets `left_at = NULL`).
- `idx_member_group_active (group_id) WHERE left_at IS NULL` — partial; serves "list members of a group" (hot path: top-bar avatars).
- `idx_member_user_active (user_id) WHERE left_at IS NULL` — partial; serves `GET /api/users/me/groups`.

FKs: `user_id → user(id)` ON DELETE CASCADE; `group_id → group(id)` ON DELETE CASCADE.

Example row:

```text
id                     | 0192d701-...-83a4
user_id                | 0192d6f0-...-0a01
group_id               | 0192d6f8-...-7b3a
display_name_override  | NULL              -- falls back to user.display_name "Jerome"
joined_at              | 2026-07-20T18:23:14+00:00
left_at                | NULL
```

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

Example row (b2b set from TML):

```text
set_id        | 0192d6fa-...-9e21
event_id      | 0192d6f8-...-7b3a   -- wait: this used to be group.event_id;
                                       in the new schema event_id on set refers
                                       to the event row's PK (unchanged).
stage_id      | 0192d6f9-...-1c4d   (PLANAXIS)
display_name  | Chris Avantgarde b2b Konstantin Sibold
day_label     | SATURDAY
starts_at     | 2026-07-25T22:30:00+02:00
ends_at       | 2026-07-26T00:00:01+02:00
external_id   | 3006674233
```

### 2.7 `artist`

Global artist registry. Unchanged.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `artist_id` | `UUID` | NO | (UUIDv7) | § 4.1. |
| `name` | `TEXT` | NO | — | Canonical display name. First-import wins. |
| `name_normalized` | `TEXT` | NO | — | `lower(NFKD(strip_diacritics(name))).strip()`, whitespace collapsed. Dedup key. |
| `image_url` | `TEXT` | YES | NULL | From source. |
| `social_links` | `JSON` | YES | NULL | Loose-shape `{spotify, instagram, soundcloud, tiktok, twitter, facebook, youtube, website}`. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |

Indexes: PK `(artist_id)`; `uq_artist_name_normalized (name_normalized)`.

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

### 2.10 `pick` (composite PK unchanged; member_id semantics carry over)

A member's intention to attend a set. Tombstoned on unpick (§ 4.6). LWW reconciliation (§ 4.5).

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `member_id` | `UUID` | NO | — | FK → member.id (now the User×Group join row). |
| `set_id` | `UUID` | NO | — | FK. |
| `state` | `TEXT` | NO | `'active'` | Enum: `active` \| `tombstoned`. |
| `state_clock_ms` | `BIGINT` | NO | — | Client-assigned epoch ms. LWW key. § 4.5. |
| `server_first_seen_at` | `TIMESTAMPTZ` | NO | `now()` | Audit. |
| `server_last_updated_at` | `TIMESTAMPTZ` | NO | `now()` | Audit + drives Last-Modified on snapshot. § 4.14. |

Indexes:

- PK `(member_id, set_id)`.
- `idx_pick_set_active (set_id) WHERE state = 'active'` — partial; per-set dot rendering.
- `idx_pick_member_active (member_id) WHERE state = 'active'` — partial; "my picks" / member-detail view.

FKs: `member_id → member(id)` ON DELETE CASCADE; `set_id → set(set_id)` ON DELETE CASCADE.

### 2.11 `artist_cache`

Spotify / Last.fm / heuristic data. Unchanged.

| Column | Type | Nullable | Default | Rationale |
|---|---|---|---|---|
| `name_normalized` | `TEXT` | NO | — | PK. Same normalization as `artist.name_normalized`. |
| `display_name` | `TEXT` | YES | NULL | UI fallback. |
| `spotify_artist_id` | `TEXT` | YES | NULL | Spotify ID once known. |
| `image_url` | `TEXT` | YES | NULL | Best image. |
| `genres` | `JSON` | YES | NULL | `string[]`. |
| `similar_artists` | `JSON` | YES | NULL | `[{name, similarity_source}]`. |
| `top_track` | `JSON` | YES | NULL | `{name, preview_url, spotify_url, image_url}`. |
| `similarity_source` | `TEXT` | YES | NULL | `spotify_v2` \| `lastfm` \| `genre_overlap` \| `none`. |
| `fetched_at` | `TIMESTAMPTZ` | YES | NULL | Last successful fetch. |
| `fetch_failure_count` | `INTEGER` | NO | `0` | Backoff per [ADR-005](ADR-005-music-data-source.md). |
| `last_failure_at` | `TIMESTAMPTZ` | YES | NULL | Backoff timestamp. |

Indexes: PK `(name_normalized)`; `idx_artist_cache_fetched (fetched_at) WHERE fetched_at IS NOT NULL`.

FKs: none (intentional).

---

## 3. Index inventory (day-1)

| Index | Table | Justifying query |
|---|---|---|
| `uq_user_username (username) WHERE username IS NOT NULL` | user | Login by username for `local`-auth users; partial because SSO users have NULL username. |
| `uq_user_email (email) WHERE email IS NOT NULL` | user | Email uniqueness for signup; future password reset; SSO users with private-relay emails fit the same constraint. |
| `uq_user_apple_subject (apple_subject_id) WHERE apple_subject_id IS NOT NULL` | user | One-User-per-Apple-identity. Lookup path for `/api/auth/apple`. |
| `uq_group_invite_code (invite_code)` | group | URL → group resolution at every group-scoped endpoint. |
| `idx_group_archive_sweep (last_active_at) WHERE archived_at IS NULL` | group | Nightly archival sweep. |
| `uq_member_user_group (user_id, group_id)` | member | One Member per (User, Group); rejoin re-activates. |
| `idx_member_group_active (group_id) WHERE left_at IS NULL` | member | Top-bar member avatars. |
| `idx_member_user_active (user_id) WHERE left_at IS NULL` | member | `GET /api/users/me/groups`. |
| `uq_event_external (source_adapter, external_id) WHERE external_id IS NOT NULL` | event | Re-import idempotency. |
| `uq_stage_external (event_id, external_id)` | stage | Re-import match. |
| `idx_stage_event_order (event_id, display_order)` | stage | Stage-column ordering. |
| `uq_set_external (event_id, external_id)` | set | Re-import match. |
| `idx_set_event_starts (event_id, starts_at)` | set | Full lineup ordered by time. |
| `idx_set_stage_starts (stage_id, starts_at)` | set | Stage-filtered calendar view. |
| `uq_artist_name_normalized (name_normalized)` | artist | Dedup on import. |
| `uq_artist_source_ext (source_adapter, external_id)` | artist_source_ref | Cross-source uniqueness. |
| `idx_setartist_artist (artist_id)` | set_artist | "All sets featuring artist X." |
| `idx_pick_set_active (set_id) WHERE state = 'active'` | pick | Per-set dot rendering. |
| `idx_pick_member_active (member_id) WHERE state = 'active'` | pick | "My picks" view. |
| `idx_artist_cache_fetched (fetched_at) WHERE fetched_at IS NOT NULL` | artist_cache | TTL refresh sweep. |

> Both SQLite (≥ 3.8.0) and Postgres support partial indexes. All `WHERE`-clause indexes above are portable.

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
WHERE  m.group_id = $1               -- uses idx_member_group_active
  AND  m.left_at  IS NULL
  AND  p.state    = 'active';        -- uses idx_pick_member_active (partial)
```

Plan: idx_member_group_active for members → PK lookup on user (for display fields) → idx_pick_member_active for active picks. No table scans.

**Q2 — Snapshot for "where will the group be at time T"** (powers `GET /api/groups/{invite_code}/snapshot`; § 4.13). Returns every set active at T or starting within the window, grouped by stage, with picker display names + avatar colors resolved.

```sql
WITH window_sets AS (
    SELECT s.set_id, s.stage_id, s.display_name, s.day_label,
           s.starts_at, s.ends_at
    FROM   set s
    WHERE  s.event_id  = $1                 -- uses idx_set_event_starts
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
                  AND m.group_id  = $2
                  AND m.left_at   IS NULL
LEFT JOIN "user" u ON u.id        = m.user_id
ORDER BY st.display_order, ws.starts_at;
```

Plan: idx_set_event_starts range scan → stage PK → idx_pick_set_active partial → member PK → user PK. Each LEFT JOIN limits to caller's group + active membership.

**Q3 — User's groups list** (powers `GET /api/users/me/groups`).

```sql
SELECT g.id, g.name, g.invite_code, g.event_id, g.created_by_user_id,
       g.last_active_at, g.archived_at, m.id AS member_id, m.joined_at
FROM   member m
JOIN   "group" g ON g.id = m.group_id
WHERE  m.user_id = $1                 -- uses idx_member_user_active
  AND  m.left_at IS NULL
ORDER BY g.last_active_at DESC;
```

**Q4 — Login by username (local-auth users only).**

```sql
SELECT * FROM "user"
WHERE auth_provider = 'local'
  AND LOWER(username) = LOWER($1);  -- uses uq_user_username (partial)
```

The DB index is partial `UNIQUE(username) WHERE username IS NOT NULL`; correctness depends on the app always writing lowercased values (§ 4.16). Login compares with `LOWER()` on both sides as defence-in-depth. SSO users sign in via `/api/auth/apple` (§ 4.20), not this query.

**Q5 — Apple Sign-In match.**

```sql
SELECT * FROM "user"
WHERE auth_provider = 'apple'
  AND apple_subject_id = $1;       -- uses uq_user_apple_subject (partial)
```

Run after the server validates Apple's identity token against Apple's JWKS and extracts the `sub` claim. No match → create new User with `auth_provider = 'apple'`; match → reuse the existing row.

---

## 4. Design decisions log

Each decision: chosen option · reasoning · alternative considered · why rejected.

### 4.1 Primary keys — UUIDv7 across the board

**Chosen.** UUIDv7 (RFC 9562) for `user`, `group`, `member`, `event`, `stage`, `set`, `artist`. `artist_cache` keys on `name_normalized` (decoupled from the registry per [ADR-005](ADR-005-music-data-source.md)).

Reasoning:

- **Time-ordered sortability** — leading 48-bit ms timestamp clusters index inserts temporally. Matters as `set` and `pick` grow.
- **No information disclosure** — sequential integer ids would leak counts; UUIDs don't.
- **Forward-compat with horizontal scale** — UUIDs are globally unique without a coordinator.

Alternative — **autoincrement BIGINT**: rejected. Information leak via API responses; horizontal-scale headaches later.

Alternative — **ULID**: rejected. Functionally similar; UUIDv7 has stronger Python ecosystem support and is an IETF standard.

Note: an earlier draft cited "offline ID generation" as a UUID benefit for `member_id`. That benefit is moot now — Member creation requires server contact (the User must be authenticated and the Group resolved); there's no client-mintable Member.

### 4.2 Time zones — `TIMESTAMPTZ` + `event.timezone`

**Chosen.** Store all timestamps as `TIMESTAMPTZ`. Store `event.timezone` as IANA name. Denormalize `set.day_label` from source.

Reasoning (unchanged from pre-pivot draft):

- `TIMESTAMPTZ` preserves the absolute instant; no DST ambiguity.
- `event.timezone` enables correct day boundaries on the FE.
- `set.day_label` keeps the source's day rollover semantics intact without re-derivation. Verified against 27 midnight-straddling rows in the TML fixture.
- The source's `+1s` end-time quirk is stored verbatim.

### 4.3 Artist deduplication — `name_normalized` with unique index

**Chosen.** `artist.name_normalized = lower(NFKD(strip_diacritics(name))).strip()` with whitespace collapsed.

Same approach is **not** applied to `user.username` — usernames are stored lowercased only (no diacritic strip), because allowing accented usernames in distinct accounts is valuable; the lowercase rule is enough to prevent the case-collision bug.

Alternative — fuzzy match for artists: rejected. False positives merge distinct artists.

### 4.4 Set ↔ Artist join — `set_artist` PK `(set_id, artist_id)` + unique `(set_id, position)`

**Chosen** (unchanged from pre-pivot). Position = source array order, 0-indexed.

### 4.5 Pick concurrency — LWW with client-assigned `state_clock_ms`

**Chosen** (unchanged). Client sends `state_clock_ms` (Unix epoch ms). Server accepts if newer; tie-break by server receive order. The server enforces that `current_user` owns the Member identified — picks-on-behalf-of is impossible.

### 4.6 Soft delete on Pick — tombstone

**Chosen** (unchanged). `state` flips between `active` and `tombstoned`; `state_clock_ms` updates on every transition. Preserves LWW correctness across out-of-order syncs.

### 4.7 Indexes — see § 3

### 4.8 External-id collisions — `(source_adapter, external_id)`; multi-source artists via `artist_source_ref`

**Chosen** (unchanged).

### 4.9 Migration ordering — everything in V001 baseline

**Chosen.** All 11 tables land in V001 (now includes `user`). Zero users at this point — clean slate.

### 4.10 Wire shape — Pydantic v2, snake_case, mirrored from the table layer

**Chosen.** See [`docs/schemas/reference/v1_pydantic.py`](../schemas/reference/v1_pydantic.py). Request and response shapes split per endpoint. snake_case end-to-end per [CLAUDE.md](../../CLAUDE.md).

### 4.11 Invite code = group's `invite_code` column, distinct from `group.id`

**Chosen.** The 8-char Crockford base32 `invite_code` is the URL-facing string (`/g/AB7K9MNP`). `group.id` (UUID) is the internal FK target. No separate `invite_token` table; no expiry; no rotation.

Reasoning:

- **Internal FK target stays UUID** for consistency with the rest of the schema and to avoid having every join carry 8 chars.
- **No expiry** matches the lifecycle ([PRD § 5.1](../PRD.md)): code lives as long as the group does (90 days inactive → archive).
- **No rotation** matches [ADR-003 superseded](ADR-003-auth-model.md) — the link is the credential equivalent for the group. Group creator can create a new group and re-invite if a code leaks.

Alternative — **single `group.code` PK** (the pre-pivot design): rejected. Made the FK column 8 chars everywhere; awkward when refactoring; the user-facing string ≠ internal id is a cleaner separation.

Alternative — **separate `invite_token` table** with TTL + rotation: rejected. Adds plumbing without v1 product need.

### 4.12 No per-Member color — `user.avatar_color` is the single source of truth

**Chosen.** Color is on `user`, not on `member`. The friends-list-spec BE-FL-002 ("assign least-used color from a 12-palette at join time") **does not apply** under the new model — a user's color is part of their account identity.

Trade-off: two users in the same group with the same avatar color will look the same. The "12 distinct colors per group" UX guarantee is broken. Flagged as a [cascade follow-up](ADR-003-auth-model.md) on the friends-list-spec.

Alternative — keep `member.color_hex` as a per-group override: rejected for v1 simplicity. Each Member row would need a color-assignment step at join; the cross-device "Jerome is always indigo" expectation would weaken.

Alternative — derive color from a hash of `user.username`: rejected. Reduces user agency over their identity color.

### 4.13 Snapshot endpoint — all-member visibility; denormalized for screenshot

**Chosen.** `GET /api/groups/{invite_code}/snapshot?at={iso_time}&window_minutes={int}` returns **every active pick from every Member of the group** within the window, NOT just the calling user's picks. The wire shape denormalizes display names and avatar colors so a single screen capture is intelligible without further lookups.

Powered by **existing indexes**; no schema change. SQL: Q2 in § 3.1.

Wire shape rules:

- Top-level: `group_name`, `event_name`, `timezone` (IANA), `snapshot_at`, `window_minutes`.
- Per stage: `name`, `display_order`, `sets[]`.
- Per set: `display_name`, `artist_names: list[str]` (denormalized — saves a per-artist lookup), `day_label`, `starts_at`, `ends_at`, `pickers: list[SnapshotMember]`.
- Per picker: `user_id`, `member_id`, `display_name` (resolved via `COALESCE(member.display_name_override, user.display_name, user.username)`), `avatar_color`.

Order: stages by `display_order` ascending; sets within a stage by `starts_at` ascending. Layout-deterministic across captures.

Reasoning (split from polled group-state): polled `/groups/{code}` runs every 15–30s (§ 4.14); snapshot is hit on user demand and can carry a heavier denormalized payload. Separating the endpoints lets each have its own cache strategy.

### 4.14 Polling cadence — 15–30s with conditional GETs (Last-Modified)

**Chosen.** The FE polls `GET /api/groups/{invite_code}` at **15s** when the calendar view is foregrounded; the snapshot endpoint `GET /api/groups/{invite_code}/snapshot` is hit on user demand and re-polled at **30s** while the snapshot view stays open. **Both endpoints** return a `Last-Modified` header derived from `MAX(pick.server_last_updated_at, member.joined_at, member.left_at)` for the group. The FE sends `If-Modified-Since`; the server returns **304 Not Modified** with no body when the group state hasn't changed.

Reasoning:

- **15s is fast enough to feel real-time** for the per-set member dots; 30s on the snapshot is fine because the user is staring at a static screen capture they'll share.
- **Conditional GETs save bandwidth** on the festival floor where mobile data is metered/spotty (extra weight on a native iOS/Android app vs a PWA — § 4.23). Most polls during quiet periods hit 304.
- **Last-Modified over ETag** — simpler. The granularity (server-assigned `TIMESTAMPTZ` to the millisecond on `pick.server_last_updated_at`) is enough. Rare same-ms churn falls back to a 200 with the fresh payload. The implementation is free to upgrade to ETag (hash of the same denormalized payload) later without a wire change — the FE accepts either header.

Alternative — **WebSockets**: deferred to v2 per [ARCHITECTURE.md § Real-time strategy](../ARCHITECTURE.md). Polling first, WS only if user reports indicate polling lag.

Alternative — **ETags**: rejected for v1. Adds a hash computation per request without a meaningful correctness improvement at this granularity.

### 4.15 Member rejoin — `(user_id, group_id)` UNIQUE; rejoin re-activates the row

**Chosen.** When an authenticated User joins a group they're already a Member of (or were, with `left_at != NULL`), the existing Member row is returned (or re-activated by setting `left_at = NULL`). No duplicate rows.

Reasoning:

- The User's identity persists across devices and sessions (§ Auth model). Rejoin is well-defined.
- Picks remain attached to the original Member row — no lost history.
- The earlier "claim by display name" flow from the pre-pivot draft is obsolete; the (User, Group) pair is the identity.

### 4.16 Username — lowercase store + lowercase compare (`local` auth_provider only)

**Chosen.** Application code lowercases on every username write (signup, `PATCH /api/users/me`). Login + lookup compare with `LOWER() = LOWER()` on both sides as defence-in-depth. Database `UNIQUE(username) WHERE username IS NOT NULL` is partial; correctness depends on the app's lowercase invariant. SSO-provider users (`auth_provider != 'local'`) have NULL username — they don't go through this query path.

Reasoning:

- Eliminates the "Jerome signs up, jerome can't log in" bug class. A reasonable engineer's lesson worth not relearning. (User referenced a sibling project's incident — re-documenting the rule here means we don't have to consult cross-project memory to know it.)
- Username uniqueness is also case-insensitive — `Jerome` and `jerome` are the same identity. Friend-of-friend confusion avoided.
- Email follows the same rule (stored lowercased; lookup `LOWER() = LOWER()`).

Alternative — **case-insensitive collation** at the column level: rejected. Postgres supports it (`citext`); SQLite doesn't portably. App-layer lowercasing is the portable choice.

### 4.17 Password hashing — argon2id (m=64 MiB, t=3, p=4)

**Chosen.** Argon2id with parameters approximating OWASP's current recommendation (post-2024 guidance): memory cost `m = 65536 KiB` (64 MiB), time cost `t = 3` iterations, parallelism `p = 4`. Stored as the full encoded string (`$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>`) so future param tuning is per-row.

Reasoning:

- **Argon2id is the modern default** — winner of the Password Hashing Competition (2015), recommended by OWASP since 2024 for new applications.
- **Memory-hard** — Argon2's memory cost defeats GPU/ASIC brute-force, where bcrypt's CPU-only cost has eroded.
- **Hybrid mode (`id`)** — resists both side-channel attacks (better in `i` mode) and TMTO attacks (better in `d` mode).

Alternative — **bcrypt**: rejected. Still widely deployed, still acceptable, but argon2id is strictly better on modern hardware. No legacy code to maintain compatibility with.

Alternative — **scrypt**: rejected. Argon2 was specifically designed to address scrypt's parameter-tuning awkwardness.

Library: `argon2-cffi` (Python). Mature, well-maintained, drop-in.

### 4.18 Email — optional in v1; no password-reset flow

**Chosen.** `user.email` is `NULL`-able. `local` signup doesn't require it. No password-reset endpoint in v1; "I forgot my password" is a manual support case.

Reasoning:

- **Lowest signup friction** — preserves a sliver of [PRD § 2 Goals](../PRD.md)' "under 30 seconds" intent post-pivot.
- **No SMTP integration in v1** — adds operational complexity.
- **Forward-compat** — adding the reset flow later requires only: an additive `password_reset_token` table + SMTP integration.

Apple-auth caveat (§ 4.20): Apple Sign-In returns an email on first authentication — either the user's real address or a private-relay address (`*@privaterelay.appleid.com`). We store whatever Apple returns verbatim. Subsequent sign-ins from the same Apple identity match on `apple_subject_id`, not email, so a user toggling their "Hide My Email" preference doesn't fork into two accounts.

Alternative — **require email at signup**: rejected. Adds friction without a v1 product benefit.

### 4.19 JWT — HS256, 24h access + 7d refresh, no v1 revocation

**Chosen.** HS256 signed with `JWT_SECRET` env var. Access token 24h, refresh token 7d. Refresh-token revocation deferred to v2 (the `jti` claim is included now so a v2 revocation table can land additively).

Reasoning:

- **HS256 over RS256** — single backend service; no need to distribute public keys.
- **24h access token** — balances UX (fewer refreshes) against blast radius if a token leaks. Refresh token at 7d covers normal usage without forcing re-login.
- **No revocation in v1** — adding a `refresh_token` table costs a DB hit per refresh. Acceptable risk for v1 (no high-value PII).

Alternative — **session cookies + server-side session store**: rejected. JWTs avoid the session store; FastAPI middleware is straightforward. v2 can add server-side state if revocation matters.

### 4.20 Apple Sign-In — v1 path if shipping on iOS

**Chosen** (pending Jerome's iOS-ship confirmation in § 5.6). Sign In with Apple is implemented in V001 with the schema columns from § 2.1 (`auth_provider = 'apple'`, `apple_subject_id`).

**Reasoning — Apple's App Store policy:**

- Per Apple's [App Review Guideline 4.8](https://developer.apple.com/app-store/review/guidelines/#sign-in-with-apple), apps that offer **any** third-party social login (Google, Facebook, Twitter, etc.) on iOS **must** also offer Sign In with Apple. Apps that offer only their own account system don't have to, but a native app that adds Google later without Apple risks reviewer rejection.
- Building Sign In with Apple from the start avoids a churn cycle when (not if) Google Sign-In is added — `auth_provider` enum already reserves the `google` value.

**Flow (native client):**

1. Native app invokes Apple's `ASAuthorizationAppleIDProvider` (iOS) / Apple's web JS (fallback).
2. Apple returns an identity token (JWT signed by Apple) + optionally `full_name` and `email` (only on first sign-in for a given app).
3. App POSTs to `POST /api/auth/apple` with `{identity_token, display_name?, email?}`.
4. Server fetches Apple's JWKS (cached), validates the token's signature + `aud` (our app's bundle id) + `iss` (`https://appleid.apple.com`) + `exp`.
5. Server extracts `sub` (Apple's stable user id), runs Q5 (§ 3.1) — match or create User.
6. Server returns `AuthResponse` (user + JWT pair, same shape as `/auth/login`).

**Forward-compat:** Google Sign-In lands later as `POST /api/auth/google` with the same response shape, populating `auth_provider = 'google'` + a separate `google_subject_id` column (additive migration; not in V001).

**Identity merging is not in scope** — a user who signs up with Apple then later wants to "link" a `local` username/password is told "create a new account or contact support." A merge flow needs a separate ADR.

Alternative — **defer Apple to post-launch**: rejected if iOS is the v1 target. Adding Apple later risks store review delays.

Alternative — **server-side login redirect (Apple OAuth on backend)**: rejected for a native app. The native SDK gives a better UX (system sheet, FaceID) and is the App Store-required path.

### 4.21 Display name — stored as-typed (preserve emojis + case)

**Chosen.** `user.display_name`, `member.display_name_override`, and `group.name` are stored verbatim — emojis preserved, casing preserved, leading/trailing whitespace stripped, internal whitespace untouched. The FE renders them as-typed.

Reasoning:

- **Identity signal.** "Sarah 🦄" and "Sarah" are different identities to the user; stripping the emoji erodes self-expression.
- **Mobile keyboard reality.** iOS/Android keyboards emit shifted-first-letter and emojis trivially; normalizing would feel adversarial.
- **No collision risk.** Display name uniqueness within a group is not enforced (group identity is `member_id`, not name); two "Sarahs" coexist.

Length: 1–80 graphemes (validated as a Unicode-grapheme count, not byte length, so a 40-emoji name stays under the cap). Pydantic validates with `min_length=1, max_length=80` on the `str` — Python's `len()` counts code points which is acceptable as a first approximation; a stricter grapheme-cluster validator can land later if abuse appears.

Username (`local` auth_provider) is separately constrained to `[a-z0-9_-]{3,32}` (§ 4.16) — that's the typed-identifier channel; display name is the expressed-identity channel.

Alternative — **normalize at write** (strip emojis, NFKC, title-case): rejected. Removes user agency for no v1 win.

### 4.22 Invite code — 8-char Crockford base32 (confirmed)

**Chosen** (confirmed, no change from earlier drafts). `group.invite_code` is 8 characters from the Crockford base32 alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ` — no `I`, `L`, `O`, `U`).

Reasoning:

- **~1.1 trillion codes** (32⁸) — safe against enumeration; a random-keyspace search at 1 RPS per IP would take longer than the heat death of common-sense patience.
- **No ambiguous characters.** Crockford strips `I`/`1`, `O`/`0`, `L`/`1`, `U` (vulgarity-adjacent) — important when users type the code from a screenshot or hear it over a voice call.
- **Mobile Share Sheet friendly.** 8 chars copy/paste cleanly; no separators required (no `XXXX-XXXX` to confuse Share Sheet parsers).
- **Url-safe.** All Crockford characters are ASCII; the code goes directly in `/g/AB7K9MNP` paths.

Server normalizes on read: uppercase input + map `i`→`1`, `l`→`1`, `o`→`0` (Crockford's canonical decode map) so a user who fat-fingers `ab7k9mnp` or `AB7K9MNO` (with `O` for `0`) gets a sensible lookup.

Alternative — **UUID short-string (base62, 6 chars)**: rejected. Smaller keyspace; case-sensitive (harder to read aloud); includes `I`/`l`/`O`/`0` ambiguities.

Alternative — **dictionary words** (`coral-piano-twelve`): rejected. Longer to type on mobile; locale-loaded (English-only); poor entropy density.

### 4.23 Mobile-native vs PWA — schema unchanged; offline store is per-platform

**Chosen (informational).** This ADR's schema design is platform-agnostic. Jerome's mobile-app direction (RN/Expo, Flutter, or native — ADR-001 revision pending, **out of scope for this PR**) does not change the server schema. It does change:

- **Client-side offline store.** Per [ADR-004](ADR-004-offline-strategy.md), the v1 offline write queue was specified as IndexedDB (PWA assumption). On a native app, the equivalent is **SQLite (iOS Core Data / Android Room / Expo's `expo-sqlite`)** or **AsyncStorage** depending on the framework. **The Pick LWW algorithm in § 4.5 is unchanged** — only the client-side serialization layer differs. ADR-004's queue prose needs updating; cascade-flagged in § 5.2.
- **Push notifications.** A native app can register for push (APNs / FCM). v1 stays poll-only; **forward-compat reservation** for `user.expo_push_token` (Expo) or `user.apns_token` + `user.fcm_token` (bare native) — flagged in § 5.8. Not in V001 — additive migration when push lands.
- **Conditional GET headers.** Same as PWA — Last-Modified / If-Modified-Since (§ 4.14). Native HTTP clients (`URLSession`, `fetch`, `OkHttp`) all support these natively.

Alternative — **continue specifying IndexedDB even on native**: rejected. Each platform has a more natural local store; forcing a PWA abstraction on a native app helps no one.

---

## 5. Open questions (flagged for Jerome)

### 5.1 PRD alignment — when?

This ADR contradicts [PRD § 1, § 2, § 4](../PRD.md). Sign-off here implies a follow-up PR to update the PRD. **Confirm:** OK to merge ADR-006 first and update PRD in a follow-up, or block this PR on the PRD update landing first?

### 5.2 ADR-004 + friends-list-spec follow-ups

- **[ADR-004 § Consequences](ADR-004-offline-strategy.md)** says "same `member_id` doesn't happen across devices in v1." That assumption is now false (one User → one Member per group → same `member_id` across all their devices). The LWW analysis still works (client clocks order the writes), but the prose needs updating. **Confirm:** follow-up PR?
- **[ADR-004 § Decision](ADR-004-offline-strategy.md)** also names "IndexedDB write queue" and "Workbox service worker" as the v1 offline store. Per § 4.23 of this ADR, native mobile would use SQLite (Core Data / Room / `expo-sqlite`) or AsyncStorage instead. **Confirm:** the ADR-004 follow-up should generalize the offline store name and split per-platform notes? (The Pick LWW algorithm in § 4.5 of this ADR is the contract; the storage layer is the implementation.)
- **[friends-list-spec BE-FL-002](../features/friends-list-spec.md)** ("least-used color from the 12-palette at join time") is now dead — color lives on User (§ 4.12). **Confirm:** follow-up PR removes BE-FL-002 and updates the per-set-dots story?

### 5.3 Client clock skew tolerance

Carried over from the pre-pivot draft. Picks LWW on `state_clock_ms` (§ 4.5). Options:

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

### 5.6 Apple Sign-In v1 — confirm in/out (bumped from "should we consider?")

**Bumped from earlier "should we?" to: Apple Sign-In is v1 if we ship on iOS.** Per Apple's [App Review Guideline 4.8](https://developer.apple.com/app-store/review/guidelines/#sign-in-with-apple), any app on iOS that offers third-party social login must also offer Sign In with Apple. Implementing it now (V001) avoids a churn cycle later when Google Sign-In is added.

The schema is wired for it (§ 2.1 columns `auth_provider`, `apple_subject_id`) and § 4.20 specifies the flow + `POST /api/auth/apple` endpoint.

**Confirm:** is iOS the v1 target?

- (A) **Yes — Apple Sign-In in V001.** Schema as designed; § 4.20 implementation in Phase 1 alongside username/password.
- (B) **No — web/PWA-only v1, Apple deferred.** Pull `auth_provider` + `apple_subject_id` from V001; promote to additive migration later. (The `auth_provider` default would still be useful to keep around as a single-value column, but it adds noise.)
- (C) **Both — iOS + Android shipping together.** Triggers also implementing Google Sign-In (Android's analog); promotes Google into V001 with a `google_subject_id` column and `POST /api/auth/google` endpoint.

**Recommendation: (A) or (C).** Building Apple now is cheap; backfilling it later is the expensive path.

### 5.7 Cross-project memory references

The earlier pivot brief referenced sibling-project memory files (e.g. `feedback_be_snake_case_json`) for the lowercase-username and snake-case-JSON rules. Those files aren't in this project; I did **not** import or cite them, and re-documented the rules in plain language here (§ 4.16) and in [CLAUDE.md § API Conventions](../../CLAUDE.md). **Confirm:** OK to treat any future sibling-project lessons the same way — document them in setlist-picker's own files rather than reference paths in another repo?

### 5.8 Push notifications — forward-compat reservation (out of scope V001)

Native apps unlock push (APNs on iOS, FCM on Android, or Expo's unified push if RN/Expo is the stack). v1 stays poll-only (§ 4.14). When push lands later, it'll need a per-device-or-per-user token column on `user` — typical shapes:

- `user.expo_push_token TEXT NULL` (single column if Expo is the stack), OR
- `user.apns_token TEXT NULL` + `user.fcm_token TEXT NULL` (separate columns for bare iOS + Android), OR
- A separate `device` table if a user has multiple devices and we want per-device subscription (the more correct long-term shape).

**Reserved** — additive migration when push is in scope. No column in V001.

**Confirm:** any preference on which shape we should plan for so the Phase 1 implementer doesn't accidentally close off the cleanest path?

---

## 6. Migration plan — V001 baseline

V001 creates 11 tables. Alembic migration order (FK dependencies):

1. `user`
2. `event`
3. `group` (FK → event, user)
4. `member` (FK → user, group)
5. `stage` (FK → event)
6. `set` (FK → event, stage)
7. `artist`
8. `artist_source_ref` (FK → artist)
9. `set_artist` (FK → set, artist)
10. `pick` (FK → member, set)
11. `artist_cache`

Then all indexes from § 3.

**Migration is out of scope for this PR.** The Phase 1 ticket reads this ADR and writes V001.

> Per [CLAUDE.md](../../CLAUDE.md), `ls services/api/alembic/versions/ | tail -5` before generating. V001 will be the first.

---

## 7. References

- [PRD.md](../PRD.md) — NB: § 1, § 2, § 4 still encode the pre-pivot anonymous model; follow-up PR required (§ 5.1).
- [ARCHITECTURE.md § Data model](../ARCHITECTURE.md) — slim summary pointing here; § Auth model updated by this PR.
- [ADR-003 — Auth model (superseded)](ADR-003-auth-model.md) — historical context preserved; supersession note appended.
- [ADR-004 — Offline strategy](ADR-004-offline-strategy.md) — Consequences section needs follow-up (§ 5.2).
- [ADR-005 — Music data source](ADR-005-music-data-source.md) — artist_cache shape, fallback chain.
- [features/calendar-spec.md](../features/calendar-spec.md)
- [features/friends-list-spec.md](../features/friends-list-spec.md) — BE-FL-002 deprecated by § 4.12; follow-up required.
- [features/artist-drilldown-spec.md](../features/artist-drilldown-spec.md)
- [`docs/schemas/reference/v1_pydantic.py`](../schemas/reference/v1_pydantic.py) — Pydantic v2 reference shapes including auth flows.
- [`.local-data/tml26-w2.json`](../../.local-data/tml26-w2.json) — round-trip fixture (gitignored).
