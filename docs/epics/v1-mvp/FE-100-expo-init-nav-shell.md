# FE-100 — Expo init + 3-tab nav shell + TanStack Query + secure-store JWT

**Wave:** 2
**Type:** FE
**Blocked by:** —
**Blocks:** FE-101, FE-102
**ADR references:** [ADR-001](../../decisions/ADR-001-tech-stack.md), [ADR-004](../../decisions/ADR-004-offline-strategy.md), EPIC OQ-01

## 1. Problem statement

There's no Expo project yet. Every FE ticket needs the workspace, navigation, query client, and JWT storage in place. This ticket creates `apps/mobile/` and ships the running shell — three bottom-nav tabs matching the prototype, no screens yet, just placeholders.

## 2. Actual solution

`apps/mobile/` initialized with `npx create-expo-app@latest --template blank-typescript`. Strip the demo content; replace `App.tsx` with a TanStack Query provider + React Navigation bottom-tabs + theme provider.

Three tabs match the prototype's `showNav` block (EPIC OQ-01: ship 3 tabs to match the prototype):

- **Home** — group list (placeholder; FE-001 fills it).
- **Search** — empty placeholder ("Coming soon").
- **You** — empty placeholder ("Coming soon"; FE-009 fills it).

Stack inside each tab uses `@react-navigation/native-stack` so Wave-3 tickets (FE-002, FE-005, etc.) push screens onto the Home stack.

JWT storage via `expo-secure-store`. Wrap with `apps/mobile/src/auth/token-store.ts` exposing `getTokens`, `setTokens`, `clearTokens`. The TanStack Query client uses an axios-equivalent fetch wrapper that reads tokens, sets the `Authorization` header, and handles 401 → trigger refresh flow → retry once.

Type-check + lint:

- `tsconfig.json` with `"strict": true`.
- ESLint with `@typescript-eslint` + `react-native`.
- Prettier formatting.

`packages/types` — placeholder for future OpenAPI codegen (post-MVP). For v1, FE types are hand-written to mirror the BE per CLAUDE.md.

API base URL via `EXPO_PUBLIC_API_URL` env var; defaults to the deployed Render URL in production.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/package.json` | Dependencies: `expo@~52`, `react-native`, `@tanstack/react-query`, `@react-navigation/{native,bottom-tabs,native-stack}`, `expo-secure-store`, `expo-router` (optional — see § 5), `expo-status-bar`, `nativewind`, `tailwindcss`. |
| `apps/mobile/app.json` | Expo config — name, slug, scheme `setlistpicker`, bundleId `com.setlistpicker.app`, package `com.setlistpicker.app`, ios/android perms (no push yet). |
| `apps/mobile/babel.config.js` | Add `nativewind/babel`. |
| `apps/mobile/tailwind.config.ts` | Empty token map — FE-101 fills it. |
| `apps/mobile/tsconfig.json` | `strict: true`, path alias `@/* → src/*`. |
| `apps/mobile/.eslintrc.cjs` | ESLint + `@typescript-eslint` + `react-hooks`. |
| `apps/mobile/App.tsx` | Root — QueryClientProvider + NavigationContainer + ThemeProvider + StatusBar. |
| `apps/mobile/src/navigation/BottomTabs.tsx` | 3 tabs with icons. |
| `apps/mobile/src/screens/placeholder/HomePlaceholder.tsx` | "GROUPS" title + "Coming soon" text. |
| `apps/mobile/src/screens/placeholder/SearchPlaceholder.tsx` | "Search coming soon". |
| `apps/mobile/src/screens/placeholder/YouPlaceholder.tsx` | "Profile coming soon". |
| `apps/mobile/src/auth/token-store.ts` | `getTokens`, `setTokens`, `clearTokens`. |
| `apps/mobile/src/api/client.ts` | `fetchWithAuth(path, init)` + base URL + 401 refresh retry. |
| `apps/mobile/src/api/queryClient.ts` | TanStack `QueryClient` with sensible defaults (15s `staleTime`, retries). |
| `apps/mobile/src/types/api.ts` | Hand-written snake_case interfaces mirroring BE Pydantic shapes. (Per CLAUDE.md NF-002 — keep aligned.) |
| `apps/mobile/.env.example` | `EXPO_PUBLIC_API_URL=http://localhost:8000`. |
| `apps/mobile/__tests__/App.smoke.test.tsx` | See § 7. |
| `apps/mobile/__tests__/api/client.test.ts` | See § 7. |
| `apps/mobile/__tests__/auth/token-store.test.ts` | See § 7. |
| `.github/workflows/mobile.yml` | CI: `npm ci`, `npm run typecheck`, `npm run lint`, `npm test`. |
| `docs/CODEBASE_GUIDE.md` | Add mobile section. |

## 4. Method signatures / new APIs

```typescript
// src/types/api.ts (snake_case — CLAUDE.md API conventions)
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

export interface ErrorResponse {
  error_code: string;
  message: string;
  request_id: string | null;
}

// ... mirror every BE Pydantic shape that v1 FE consumes
```

```typescript
// src/auth/token-store.ts
export async function getTokens(): Promise<TokenPair | null>;
export async function setTokens(pair: TokenPair): Promise<void>;
export async function clearTokens(): Promise<void>;
```

```typescript
// src/api/client.ts
export async function fetchWithAuth<T>(
  path: string,
  init?: RequestInit,
): Promise<T>;
```

`fetchWithAuth` algorithm:

1. Resolve URL = `EXPO_PUBLIC_API_URL + path`.
2. Read `access_token` from secure-store.
3. Set `Authorization: Bearer ...` and `Content-Type: application/json` if body.
4. Call `fetch`.
5. If 401 AND haven't retried: POST `/api/auth/refresh` with `refresh_token`; on success, store new pair, retry once. On failure, `clearTokens()` and throw `UnauthenticatedError`.
6. If 2xx: parse JSON, return typed.
7. If 4xx/5xx: parse `ErrorResponse`; throw typed error.

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Bottom-nav tab count | 3 | EPIC OQ-01. |
| Default `staleTime` | 15_000 ms | Matches the 15s group-state poll cadence. |
| API base URL env | `EXPO_PUBLIC_API_URL` | Expo's public-prefix convention. |
| Navigation framework | `@react-navigation/*` (NOT `expo-router`) | Stable; widely documented; manual stacks let us model the prototype's nested stacks explicitly. (Expo-router would also work; choose React Navigation for less magic.) |
| Splash screen | Default Expo splash with cosmic-bg color `#0a0712` | Matches DESIGN-TOKENS `bg.canvas`. |
| Status bar style | `light` | All screens are dark. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| User opens app with no stored tokens | Bottom nav shows; tapping any tab routes to FE-102 auth screen. |
| User opens app with valid stored tokens | Goes straight to Home tab. |
| User opens app with expired access token + valid refresh | First request triggers 401 → refresh → retry. UI shows briefly empty then populated. |
| User opens app with expired refresh | Refresh fails → `clearTokens()` → navigate to FE-102. |
| `EXPO_PUBLIC_API_URL` not set | Use a localhost default in dev; production build's `app.json` `extra` field must set it via `EXPO_PUBLIC_API_URL=...` at build time. |
| Network offline at boot | TanStack Query's `networkMode: "offlineFirst"` lets cached data render; UI shows offline badge (FE-101 ships the badge primitive). |
| 401 from a non-auth endpoint with no refresh token | Treat as `UnauthenticatedError`; navigate to FE-102. |
| Slow Android device | Splash should hide only after `useFonts(...)` completes — load via `expo-font` synchronously at app boot. |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `__tests__/App.smoke.test.tsx` | `app_renders_without_throwing` | `render(<App />)` doesn't throw. |
| `__tests__/App.smoke.test.tsx` | `bottom_tabs_show_three_labels` | After render, the labels `"Home"`, `"Search"`, `"You"` are present. |
| `__tests__/api/client.test.ts` | `fetch_with_auth_attaches_bearer_token` | Mock secure-store → `getTokens` returns; mock fetch → `Authorization` header present. |
| `__tests__/api/client.test.ts` | `fetch_with_auth_refreshes_on_401_then_retries_once` | First 401, second 200 → returns 200's body; refresh endpoint called exactly once; original retried once. |
| `__tests__/api/client.test.ts` | `fetch_with_auth_clears_tokens_on_refresh_failure` | 401 then refresh fails → `clearTokens` called → throws `UnauthenticatedError`. |
| `__tests__/api/client.test.ts` | `fetch_with_auth_parses_error_response` | 400 with `ErrorResponse` body → throws with `error_code`. |
| `__tests__/auth/token-store.test.ts` | `set_then_get_round_trips` | Mock secure-store; set → get → equal. |
| `__tests__/auth/token-store.test.ts` | `clear_removes_both_keys` | After clear, both `access_token` and `refresh_token` removed. |

**Manual QA:**

1. `cd apps/mobile && npx expo start` — Metro starts.
2. Press `i` → iOS simulator boots; bottom nav with 3 tabs visible.
3. Tap each tab → placeholder text shows.
4. Cmd-D → Reload → app rebuilds quickly.
5. `npm run typecheck` — 0 errors.
6. `npm run lint` — 0 violations.
7. `npm test` — green.

**Structured-log lines:** N/A — FE.

**Failure modes:**

- Missing fonts → splash hangs. Tests catch via `useFonts` mock.
- Bad `EXPO_PUBLIC_API_URL` → all fetches fail with network error. Surface as a toast (FE-101 ships the toast).

## 8. Out of scope

| Item | Where |
|---|---|
| Auth screens | FE-102. |
| Token-refresh background daemon | Refresh is reactive — only on 401. |
| Offline persistence of TanStack cache | Use `expo-sqlite` via `@tanstack/query-async-storage-persister` — out of v1 plumbing (BACKLOG-019); v1 relies on `staleTime` + the 15s poll. |
| Deep-linking config beyond the scheme | BACKLOG-020. |
| 5-tab nav (Favorites / Schedules / Artists) | OQ-01 — v2 promotion. |
| Push notifications wiring on app side | v1.x. |

## 9. Structured-log events

N/A — FE. Errors surface as TanStack Query error states; FE-101 ships the visual treatment.

## 10. Rollback plan

Revert. `apps/mobile/` disappears; no shipped binaries yet. Wave-3 work waits.
