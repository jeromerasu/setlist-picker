# Codebase Guide — setlist-picker

This guide stays current as code lands. Every PR that adds, removes, or renames a module / class / endpoint MUST update this file (per [CLAUDE.md](../CLAUDE.md) hard rules). It's the orientation map for new contributors and AI sessions — keep it terse, file-by-file, no prose paragraphs inside the package tables.

## Architecture

| Surface | Language / Framework | Notes |
|---|---|---|
| Web client | TypeScript + Next.js (App Router) + PWA | `apps/web/` |
| Backend API | Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Pydantic v2 | `services/api/` |
| Shared types | TypeScript types generated from OpenAPI | `packages/types/` |
| Datastore | Postgres 16 (asyncpg); Alembic migrations | `services/api/alembic/` |
| Build orchestration | Turborepo for TS apps + packages; `uv` for Python service | `turbo.json`, `services/api/pyproject.toml` |

## Data model + auth

The v1 data schema (users, groups, members, events, stages, sets, artists, picks, artist_cache) AND the auth model (JWT-based with username + password) are specified in [decisions/ADR-006-initial-data-schema.md](decisions/ADR-006-initial-data-schema.md). ADR-006 supersedes [ADR-003](decisions/ADR-003-auth-model.md) (anonymous group-code access). The Pydantic wire-shape reference for every v1 endpoint — including the auth flows — lives at [schemas/reference/v1_pydantic.py](schemas/reference/v1_pydantic.py); it's a design artifact, not yet wired into `services/api/`. Every PR that adds or renames a column or endpoint MUST update ADR-006 (or supersede it with ADR-NNN) and the Pydantic reference.

## Backend entry points

| File | Purpose |
|---|---|
| `services/api/app/main.py` | `create_app()` factory + module-level `app` export |
| `services/api/app/routes/health.py` | `GET /healthz` — liveness probe |
| `services/api/app/routes/auth.py` | `POST /api/auth/signup`, `/login`, `/refresh`, `/apple`, `/google` |
| `services/api/app/routes/users.py` | `GET /api/users/me`, `PATCH /api/users/me`, `GET /api/users/me/groups`, `POST /api/users/me/devices`, `DELETE /api/users/me/devices/{device_id}` |
| `services/api/app/routes/groups.py` | `POST /api/groups`, `POST /api/groups/join`, `GET /api/groups/{invite_code}`, `GET /api/groups/{invite_code}/snapshot` |
| `services/api/app/routes/events.py` | `GET /api/events`, `GET /api/events/{event_id}/lineup`, `POST /api/events/import` (admin) |
| `services/api/app/routes/artists.py` | `GET /api/artists/{artist_name}` — cache-first, Spotify+Last.fm+genre-overlap; 503 on total miss |
| `services/api/app/routes/picks.py` | `POST /api/groups/{invite_code}/picks`, `POST .../picks/sync`, `DELETE .../picks/{set_id}` |

## `services/api/`

### `services/api/app/`

| File | Purpose |
|---|---|
| `app/__init__.py` | Package marker |
| `app/main.py` | `create_app(settings?)` — FastAPI factory with lifespan logging |
| `app/config.py` | `Settings(BaseSettings)` — env-var loader (pydantic-settings) |
| `app/logging.py` | `configure_logging(level)` — installs structlog JSON renderer |

### `services/api/app/routes/`

| File | Purpose |
|---|---|
| `routes/__init__.py` | Package marker |
| `routes/health.py` | `GET /healthz` → `{"status":"ok","service":"setlist-picker-api"}` |
| `routes/auth.py` | Signup, login, refresh, Apple Sign-In, Google Sign-In |
| `routes/users.py` | `GET /PATCH /api/users/me` — authenticated user profile |

### `services/api/app/db/`

| File | Purpose |
|---|---|
| `db/__init__.py` | Re-exports `Base`, `async_session_maker`, `get_db` |
| `db/base.py` | `Base(DeclarativeBase)` + `TIMESTAMPTZ` type alias |
| `db/uuid7.py` | `uuid7() -> uuid.UUID` wrapper around `uuid_utils.uuid7()` |
| `db/session.py` | Lazy-init `AsyncEngine`, `get_session_maker()`, `get_db()` FastAPI dep |
| `db/models/user.py` | `User` ORM model (ADR-006 § 2.1) |
| `db/models/event.py` | `Event` ORM model (§ 2.4) |
| `db/models/group.py` | `Group` ORM model (§ 2.2) |
| `db/models/member.py` | `Member` ORM model (§ 2.3) |
| `db/models/device.py` | `Device` ORM model (§ 2.12) |
| `db/models/stage.py` | `Stage` ORM model (§ 2.5) |
| `db/models/set_.py` | `Set` ORM model (§ 2.6; named `set_.py` to avoid Python builtin conflict) |
| `db/models/artist.py` | `Artist`, `ArtistSourceRef`, `SetArtist` ORM models (§ 2.7–2.9) |
| `db/models/pick.py` | `Pick` ORM model (§ 2.10) |
| `db/models/artist_cache.py` | `ArtistCache` ORM model (§ 2.11) |
| `db/models/group_activity.py` | `GroupActivity` ORM model (§ 2.13) |

### `services/api/app/auth/`

| File | Purpose |
|---|---|
| `auth/__init__.py` | Re-exports all auth symbols |
| `auth/hashing.py` | `hash_password`, `verify_password`, `dummy_verify` (argon2-cffi; timing-safe) |
| `auth/jwt.py` | `encode_access`, `encode_refresh`, `decode`; `Claims` Pydantic model |
| `auth/palette.py` | `AVATAR_PALETTE` — 12 hex colors for deterministic avatar assignment |
| `auth/dependencies.py` | `current_user` FastAPI dep — decodes Bearer token, loads User, logs rejections |
| `auth/admin.py` | `current_admin` FastAPI dep — `X-Admin-Token` header; constant-time compare; 401 on mismatch |
| `auth/jwks.py` | `fetch_jwks(url)` — shared JWKS fetcher with 1h TTL cache (cachetools) |
| `auth/apple.py` | `AppleClaims`, `validate_apple_identity_token` — RS256 JWT + iss/aud check |
| `auth/google.py` | `GoogleClaims`, `validate_google_id_token` — RS256 JWT + both iss forms |
| `auth/invite_code.py` | `generate_invite_code()`, `normalize()` — Crockford Base32 (8 chars, I→1/L→1/O→0) |

### `services/api/app/schemas/`

| File | Purpose |
|---|---|
| `schemas/auth.py` | `UserCreate`, `UserLogin`, `TokenPair`, `AuthResponse`, `TokenRefreshRequest`, `AppleSignInRequest`, `GoogleSignInRequest`, `UserOut`, `UserUpdate` |
| `schemas/groups.py` | `GroupCreate`, `GroupCreateResponse`, `GroupJoinRequest`, `MemberOut`, `MyGroupListItem`, `GroupJoinResponse`, `MyGroupListResponse`, `EventSummary`, `PickSummary`, `GroupStateResponse` |
| `schemas/events.py` | `EventListItem`, `EventListResponse`, `ArtistRef`, `SetDetail`, `StageDetail`, `EventLineupResponse` |
| `schemas/picks.py` | `PickCreate`, `PickResult`, `PickSyncRequest`, `PickSyncResponse`, `PickRemoveRequest` |
| `schemas/snapshot.py` | `SnapshotMember`, `SnapshotSet`, `SnapshotStage`, `GroupSnapshotResponse` |
| `schemas/lineup.py` | `LineupSourceArtist`, `LineupSourceStage`, `LineupSourcePerformance`, `LineupImportRequest`, `LineupImportResponse` |
| `schemas/artists.py` | `ArtistDetailResponse`, `SimilarArtist`, `TopTrack`, `CacheStatus` |
| `schemas/devices.py` | `DeviceRegisterRequest`, `DeviceOut`, `DeviceRevokeResponse`, `DevicePlatform`, `PushProvider` |

### `services/api/app/services/`

| File | Purpose |
|---|---|
| `services/user_service.py` | `create_local_user`, `authenticate`, `patch_user`, `get_or_create_apple_user`, `get_or_create_google_user` — IntegrityError handled via `begin_nested()` |
| `services/activity_service.py` | `ActivityKind` enum, `log_activity()` — inserts `GroupActivity` rows |
| `services/group_service.py` | `create_group`, `join_group`, `list_my_groups`, `get_group_state` |
| `services/member_service.py` | `resolve_member_out`, `resolve_member_out_batch` — COALESCE display_name_override → display_name → username → "Member" |
| `services/event_service.py` | `list_events`, `get_event_lineup` — ILIKE search and full lineup with stages/sets/artists |
| `services/pick_service.py` | `upsert_pick`, `upsert_picks_batch` — LWW upsert with clock-skew guard and activity logging |
| `services/snapshot_service.py` | `get_snapshot` — Q2 query: sets in window + stage + active picks + member/user denormalized |
| `services/artist_normalize.py` | `normalize(name)` — lower → NFKD → strip diacritics → collapse whitespace |
| `services/lineup_import_service.py` | `import_lineup` — full event/stage/set/artist UPSERT in one transaction; LWW for spotify/image; merge social_links |
| `services/artist_service.py` | `get_artist_detail` — cache-first (7d TTL), exponential backoff on failure, fan-out to Spotify+Last.fm+genre-overlap |
| `services/artist_prewarm.py` | `prewarm_artists_from_event` — background batch populate for all artists in an event; 5-concurrent cap |
| `services/artist_providers/spotify.py` | `SpotifyProvider` — client-credentials token cache, search+top-tracks; raises `RateLimited` on 429 |
| `services/artist_providers/lastfm.py` | `LastFmProvider` — `artist.getsimilar`; returns `[]` on 5xx |
| `services/artist_providers/genre_overlap.py` | `GenreOverlapProvider` — Jaccard similarity over `artist_cache.genres` rows |
| `services/artist_providers/protocol.py` | `MusicDataProvider`, `SimilarArtistsProvider` Protocols; `ProviderArtist`, `RateLimited` |
| `services/device_service.py` | `register_device`, `revoke_device`; `DeviceNotFoundError` |

### `services/api/scripts/`

| File | Purpose |
|---|---|
| `scripts/import_lineup.py` | CLI: `--file`, `--event-name`, `--start-date`, `--end-date`, `--timezone`, `--source-adapter`, `--external-id` → calls `import_lineup` via `AsyncSession` |

### `services/api/app/utils/`

| File | Purpose |
|---|---|
| `utils/http_dates.py` | `format_last_modified`, `parse_if_modified_since` — RFC 7231 IMF-fixdate helpers |

### `services/api/app/middleware/`

| File | Purpose |
|---|---|
| `middleware/request_id.py` | `RequestIdMiddleware` — injects `request_id` UUID into structlog context per request |

### `services/api/alembic/`

| File | Purpose |
|---|---|
| `alembic/env.py` | Async-aware migration runner (`asyncio.run(run_async_migrations())`) |
| `alembic/versions/0001_v001_baseline.py` | V001 hand-written migration: 13 tables + 27 indexes per ADR-006 |

## Schema

The full schema is specified in [ADR-006](decisions/ADR-006-initial-data-schema.md). V001 creates 13 tables: `user`, `event`, `group`, `member`, `device`, `stage`, `set`, `artist`, `artist_source_ref`, `set_artist`, `pick`, `artist_cache`, `group_activity`.

## `apps/mobile/`

React Native + Expo SDK 52 mobile app. Run with `npx expo start` from `apps/mobile/`.

### Entry points

| File | Purpose |
|---|---|
| `apps/mobile/App.tsx` | Root: `QueryClientProvider` + `NavigationContainer` + `StatusBar` + `BottomTabs` |
| `apps/mobile/src/navigation/BottomTabs.tsx` | 3-tab shell: Home / Search / You |
| `apps/mobile/src/screens/placeholder/*.tsx` | Wave-1 placeholder screens; Wave-3 tickets fill real content |

### `apps/mobile/src/`

| File / Dir | Purpose |
|---|---|
| `src/api/client.ts` | `fetchWithAuth<T>` — base-URL + Bearer + 401→refresh→retry; `ApiError`, `UnauthenticatedError` |
| `src/api/queryClient.ts` | TanStack `QueryClient` (15s `staleTime`, offline-first) |
| `src/auth/token-store.ts` | `getTokens / setTokens / clearTokens` — `expo-secure-store` wrapper |
| `src/types/api.ts` | Snake_case TypeScript interfaces mirroring BE Pydantic shapes |
| `src/theme/tokens.ts` | Single source of truth: `colors`, `gradients`, `radius`, `spacing`, `sizes`, `motion` constants |
| `src/theme/fonts.ts` | `FONT_MAP` — 14 Orbitron / Playfair / Manrope / SpaceMono / VT323 entries (TTFs in `assets/fonts/`) |
| `src/theme/motion.ts` | Re-exports `motion` from tokens + `easing` presets |
| `src/theme/spacing.ts` | Re-exports `spacing` + `sizes` from tokens |
| `src/components/GlassCard.tsx` | `<GlassCard variant border withInsetHighlight>` — glass surface container |
| `src/components/Avatar.tsx` | `<Avatar initials color size ringColor>` — single circle avatar |
| `src/components/AvatarStack.tsx` | `<AvatarStack members size>` — overlapping row, +N overflow badge |
| `src/components/StageDot.tsx` | `<StageDot color size withGlow>` — per-stage timeline dot |
| `src/components/NeonGradientButton.tsx` | `<NeonGradientButton label onPress disabled size>` — primary CTA |
| `src/components/GradientText.tsx` | `<GradientText font weight size>` — gradient-filled display text |
| `src/components/GlassBottomNav.tsx` | `<GlassBottomNav items>` — glass floating nav bar |
| `src/components/PillTab.tsx` | `<PillTab label active onPress>` — segment pill |
| `src/components/OutlineButton.tsx` | `<OutlineButton label onPress>` — bordered secondary button |
| `src/components/BackChip.tsx` | `<BackChip onPress>` — round back button |
| `src/components/SearchInput.tsx` | `<SearchInput value onChangeText placeholder>` — styled search field |
| `src/components/EmptyState.tsx` | `<EmptyState icon title body cta>` — full-screen empty placeholder |
| `src/auth/AuthContext.tsx` | `AuthProvider` + `useAuth()` hook — JWT state, `signIn(pair)`, `signOut()` |
| `src/auth/useLocalAuth.ts` | `useLocalAuth()` — `login(username, password)` + `signup(username, password, display_name)` |
| `src/auth/useAppleSignIn.ts` | `useAppleSignIn()` — stub for Wave-3 expo-apple-authentication wiring |
| `src/auth/useGoogleSignIn.ts` | `useGoogleSignIn()` — stub for Wave-3 expo-auth-session wiring |
| `src/screens/auth/AuthLanding.tsx` | Landing screen: Apple / Google / email CTAs |
| `src/screens/auth/LocalLogin.tsx` | Email+password login form |
| `src/screens/auth/LocalSignup.tsx` | Account creation form |
| `src/navigation/AuthStack.tsx` | `AuthStack` — native-stack for `AuthLanding → LocalLogin / LocalSignup`; `AuthStackParamList` type |
| `src/navigation/RootNavigator.tsx` | `RootNavigator` — renders `AuthStack` or `BottomTabs` based on `isAuthenticated` |

### `apps/mobile/__tests__/`

| File | Tests |
|---|---|
| `App.smoke.test.tsx` | Renders without throwing; 3 tab labels present |
| `api/client.test.ts` | Bearer header; 401-refresh-retry; clearTokens on refresh failure; error parsing |
| `auth/token-store.test.ts` | Round-trip; clear removes keys |
| `components/primitives.test.tsx` | 21 snapshot tests covering all 12 FE-101 primitive components |
| `auth/AuthContext.test.tsx` | 5 tests: loading state, stored tokens restore auth, signIn/signOut, hook-outside-provider throws |
| `auth/useLocalAuth.test.ts` | 5 tests: login 200, login error, network error, signup 200, snake_case body |
| `screens/AuthLanding.test.tsx` | 3 tests: CTA presence, email→LocalLogin, signup link→LocalSignup |
| `screens/LocalLogin.test.tsx` | 3 tests: disabled when empty, submit calls login+signIn, back chip goBack |

### Config

| File | Purpose |
|---|---|
| `app.json` | Expo config — scheme `setlistpicker`, dark mode |
| `babel.config.js` | `babel-preset-expo` (+ `nativewind/babel` outside test env) |
| `tailwind.config.ts` | DESIGN-TOKENS full color/font/spacing/radius map |
| `tsconfig.json` | `strict: true`, `@/* → src/*` alias |
| `.eslintrc.cjs` | `@typescript-eslint` + `react-hooks`; snake_case allowed for API types |

## `apps/web/`

Stub — no content yet.

## `packages/types/`

Stub.

| File | Purpose |
|---|---|
| _(none yet)_ | |

## Cross-repo interactions

(N/A — setlist-picker is self-contained. This section will populate if the project ever splits across multiple repos.)

## Invariants

- **snake_case wire JSON.** Backend Pydantic models use snake_case fields (PEP 8). Frontend TypeScript interfaces use snake_case fields to match the wire. ESLint warnings about naming convention are disabled for API types.
- **`'use client'` directive on line 1** for every interactive Next.js component. NF-001 in [code_review_known_fixes.md](code_review_known_fixes.md).
- **No bare `except Exception`** in service-layer code. NF-002 in [code_review_known_fixes.md](code_review_known_fixes.md).
- **Defensive rendering.** Frontend `.map` / `.length` / `.some` against query data must guard for `undefined`. NF-003.
- **No top-level browser-API reads** in SSR-shared code. NF-004.

## How to update this guide

- After your PR is merged, audit the package tables for new files you added.
- New endpoints go in `Backend entry points` AND in the appropriate `app/api/` table.
- New shared types go in `packages/types`.
- New dependencies go in the appropriate package table (`pyproject.toml` for Python, `package.json` for TS).
- Don't bloat purpose cells — 1–2 sentences max.

### FE-001 — Groups list (Home screen)

| File | Purpose |
|---|---|
| `src/navigation/types.ts` | `HomeStackParamList` — nav param types for all Home-stack screens |
| `src/navigation/HomeStack.tsx` | Home tab's native stack; `GroupsList` as root |
| `src/theme/heroes.ts` | `HUES[6]` gradient pairs + `getHue(index)` helper |
| `src/hooks/useMyGroups.ts` | TanStack Query hook → `GET /api/users/me/groups`; `staleTime: 15s` |
| `src/screens/groups/GroupCard.tsx` | Tappable card: hero-color band + group name + archived pill |
| `src/screens/groups/GroupsList.tsx` | Home screen: scroll of GroupCards + empty/error states + Create/Join CTAs |
| `__tests__/hooks/useMyGroups.test.ts` | 2 tests: data returned, hook function exists |
| `__tests__/components/GroupCard.test.tsx` | 4 tests: renders, tap, truncation, archived pill |
| `__tests__/screens/GroupsList.test.tsx` | 7 tests: empty, N cards, create/join nav, refresh, HUES rotation, error |

### FE-002 — Create group form

| File | Purpose |
|---|---|
| `src/hooks/useCreateGroup.ts` | Mutation hook → `POST /api/groups`; returns `GroupCreateResponse` |
| `src/screens/groups/CreateGroup.tsx` | 2-field form: group name + event button; `navigation.replace('GroupDetail')` on success |
| `__tests__/hooks/useCreateGroup.test.ts` | 1 test: POST body has name + event_id |
| `__tests__/screens/CreateGroup.test.tsx` | 7 tests: renders, disabled, enabled, whitespace, nav, route-param fill, mutate |

### FE-003 — Event picker

| File | Purpose |
|---|---|
| `src/utils/eventTile.ts` | `deriveMono(name)` + `deriveTileGradient(name)` — stable hash-based tile appearance |
| `src/hooks/useEvents.ts` | Debounced TanStack query → `GET /api/events?q=`; 300ms debounce; staleTime: 60s |
| `src/screens/groups/EventPicker.tsx` | Search + list of events with 46×46 mono-letter tiles; tap navigates back with selectedEvent |
| `__tests__/utils/eventTile.test.ts` | 5 tests: mono extraction, special chars, fallback, tile stability |
| `__tests__/hooks/useEvents.test.ts` | 2 tests: q param passed, debounce batching |
| `__tests__/screens/EventPicker.test.tsx` | 5 tests: renders events, search triggers, empty state, tap nav, back chip |

### FE-004 — Join group

| File | Purpose |
|---|---|
| `src/utils/inviteCode.ts` | `normalizeCode(raw)` — uppercase + Crockford B32 substitutions (I→1, L→1, O→0), clips to 8 chars |
| `src/hooks/useJoinGroup.ts` | Mutation → `POST /api/groups/join` with normalized invite_code |
| `src/screens/groups/JoinGroup.tsx` | Code input (maxLength 8); submit enabled when code=8; on success replaces to GroupDetail; 404→inline error |
| `__tests__/utils/inviteCode.test.ts` | 5 tests: uppercase, I→1, L→1, O→0, clip |
| `__tests__/screens/JoinGroup.test.tsx` | 8 tests: renders, enabled, disabled, normalization, back, mutate, success nav, 404 error |

### FE-005 — Group detail

| File | Purpose |
|---|---|
| `src/utils/dayBuckets.ts` | `bucketByDay(sets)` — preserves insertion order; `pickedSetIds(picks, myMemberId?)` |
| `src/utils/inviteShare.ts` | `shareInvite(name, code)` — RN Share.share wrapper |
| `src/hooks/useGroupState.ts` | TanStack query → `GET /api/groups/:invite_code`; staleTime 15s |
| `src/hooks/useEventLineup.ts` | TanStack query → `GET /api/events/:id/lineup`; staleTime Infinity; disabled when no eventId |
| `src/hooks/usePickToggle.ts` | Mutation → `POST /DELETE /api/groups/:invite_code/picks/:set_id`; invalidates group query on success |
| `src/screens/groups/GroupDetailHeader.tsx` | Name + code + share + schedule/snapshot pills |
| `src/screens/groups/ArtistRowAll.tsx` | Artist row with Avatar (djb2 color) + heart pick toggle + member count |
| `src/screens/groups/GroupDetail.tsx` | Root screen; day-bucketed artist list; loading / error states |
| `__tests__/utils/dayBuckets.test.ts` | 3 tests: bucket grouping, empty, pickedSetIds |
| `__tests__/screens/GroupDetail.test.tsx` | 9 tests: renders, day buckets, loading, error, toggle, nav artist, schedule, snapshot, picked heart |

### FE-006 — Schedule

| File | Purpose |
|---|---|
| `src/utils/gridLayout.ts` | `setTop`, `setHeight`, `groupByStage`, `timeToMinutes` — pixel math for grid layout |
| `src/utils/dayList.ts` | `uniqueDays(sets)` (insertion-order), `setsForDay(sets, day)` |
| `src/hooks/useScheduleData.ts` | Composes useGroupState + useEventLineup → `{ sets, eventName, isLoading }` |
| `src/hooks/useUpNext.ts` | Finds nearest upcoming set relative to `nowIso` (or Date.now()) |
| `src/screens/schedule/DayMenu.tsx` | Horizontal scrollable day tab pills |
| `src/screens/schedule/Timeline.tsx` | Absolute-positioned hour labels + tick lines overlay (pointerEvents=none) |
| `src/screens/schedule/AllStagesGrid.tsx` | Dual-scroll (h+v) stage columns with absolute-positioned set blocks |
| `src/screens/schedule/Schedule.tsx` | Root: DayMenu + AllStagesGrid; tap set → ArtistDetail |
| `__tests__/utils/gridLayout.test.ts` | 6 tests: timeToMinutes, setTop, setHeight, clamp, groupByStage |
| `__tests__/utils/dayList.test.ts` | 3 tests: uniqueDays order, empty, setsForDay filter |
| `__tests__/hooks/useUpNext.test.ts` | 3 tests: nearest upcoming, all past, empty |
| `__tests__/screens/Schedule.test.tsx` | 6 tests: event name, day tabs, tab switch, set tap nav, loading, back |

### FE-007 — Artist detail (cyber-retro)

| File | Purpose |
|---|---|
| `src/theme/cyber.ts` | Cyber-retro design tokens: neon pink/cyan/green/acid-yellow, dark bg |
| `src/hooks/useArtistDetail.ts` | TanStack query → `GET /api/artists/:name`; staleTime Infinity |
| `src/hooks/useAudioPreview.ts` | `play(url)` / `stop()` via expo-av; `isPlaying` state |
| `src/screens/artist/ArtistDetail.tsx` | Genres + top_track preview (single) + similar artists → push ArtistDetail |
| `src/types/global.d.ts` | Stub `expo-av` module declaration (package not yet installed) |
| `src/__mocks__/expo-av.ts` | Jest mock for expo-av |
| `__tests__/screens/ArtistDetail.test.tsx` | 9 tests: name, genres, track, play, null track, similar nav, loading, error, back |

### FE-008 — Right Now snapshot

| File | Purpose |
|---|---|
| `src/hooks/useSnapshot.ts` | TanStack query → `GET /api/groups/:code/snapshot?at=`; staleTime 30s |
| `src/utils/captureScreenshot.ts` | `captureAndShare(ref, filename)` — react-native-view-shot + RN Share |
| `src/screens/snapshot/RightNowSnapshot.tsx` | Flattens stages→sets; AvatarStack shows pickers; share button captures card |
| `src/__mocks__/react-native-view-shot.ts` | Jest stub (package not installed; stubbed in moduleNameMapper) |
| `__tests__/screens/RightNowSnapshot.test.tsx` | 6 tests: header, set rows, loading, error, back, empty state |

### FE-009 — Account profile

| File | Purpose |
|---|---|
| `src/hooks/useUpdateProfile.ts` | Mutation → `PATCH /api/profile` with display_name + avatar_color |
| `src/hooks/useLeaveGroup.ts` | Mutation → `DELETE /api/groups/:code/leave`; invalidates my-groups on success |
| `src/screens/profile/AvatarColorPicker.tsx` | 10-swatch color palette with selected ring highlight |
| `src/screens/profile/LeaveGroupModal.tsx` | Bottom-sheet modal with cancel/confirm (danger) actions |
| `src/screens/profile/AccountProfile.tsx` | Name input + color picker + save; group list with Leave; sign out |
| `__tests__/screens/AccountProfile.test.tsx` | 10 tests: input, save disabled/enabled, payload, swatch, groups, modal, confirm, cancel, sign out |
