# FE-102 — Auth flow: Apple / Google / local (signup + login)

**Wave:** 2
**Type:** FE
**Blocked by:** FE-100, FE-101, BE-003, BE-004, BE-005
**Blocks:** every Wave-3 FE ticket
**ADR references:** [ADR-006 § 4.20, § 4.24](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

First chrome the user sees on a fresh install. Three sign-in paths: Apple (iOS-prominent), Google (cross-platform), local username/password (fallback). The screen funnels into the home tab on success.

## 2. Actual solution

Three screens managed by an `AuthStack` rendered ABOVE the BottomTabs when `tokens === null`:

- `AuthLanding` — full-bleed cosmic background, big "Setlist" logotype (GradientText, Orbitron 900 40px). Three CTAs: "Continue with Apple", "Continue with Google", "Continue with username".
- `LocalLogin` — form: username + password. Bottom toggles "Don't have an account? Sign up."
- `LocalSignup` — form: username + password + optional email + display_name. Bottom toggles "Already have an account? Sign in."

Native auth modules:

- `expo-apple-authentication` — iOS only. Renders Apple's native button per their HIG.
- `expo-auth-session` with `@react-native-google-signin/google-signin` — both platforms. Android uses Google's native SDK; iOS uses `expo-auth-session` web flow.

On success of any flow: store the `TokenPair` via `setTokens`; invalidate auth-gated TanStack queries; navigation re-renders BottomTabs root.

Error handling: surface BE error_code via toast (FE-101's primitive). The five v1 codes (`username_taken`, `email_taken`, `invalid_credentials`, `apple_token_invalid`, `google_token_invalid`) each get human copy.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/package.json` | Add `expo-apple-authentication`, `@react-native-google-signin/google-signin`, `expo-auth-session`, `expo-web-browser`, `expo-crypto`. |
| `apps/mobile/app.json` | `ios.usesAppleSignIn: true`; google plugin config with iOS/Android client IDs. |
| `apps/mobile/src/navigation/AuthStack.tsx` | New stack. |
| `apps/mobile/src/navigation/RootNavigator.tsx` | Switch — AuthStack if `tokens==null` else BottomTabs. |
| `apps/mobile/src/screens/auth/AuthLanding.tsx` | Landing. |
| `apps/mobile/src/screens/auth/LocalLogin.tsx` | Login form. |
| `apps/mobile/src/screens/auth/LocalSignup.tsx` | Signup form. |
| `apps/mobile/src/auth/useAppleSignIn.ts` | Hook — wraps `expo-apple-authentication`, POSTs to BE-004. |
| `apps/mobile/src/auth/useGoogleSignIn.ts` | Hook — wraps Google SDK + posts to BE-005. |
| `apps/mobile/src/auth/useLocalAuth.ts` | Hooks — `useLocalLogin`, `useLocalSignup`. |
| `apps/mobile/src/auth/AuthContext.tsx` | Provides `tokens`, `user`, `signOut()`. Refreshes on app foreground. |
| `apps/mobile/src/components/AuthFormField.tsx` | Reusable input row. |
| `apps/mobile/src/components/AppleButton.tsx` | Native Apple-styled button. |
| `apps/mobile/src/components/GoogleButton.tsx` | Google-styled button. |
| `apps/mobile/__tests__/screens/AuthLanding.test.tsx` | See § 7. |
| `apps/mobile/__tests__/screens/LocalLogin.test.tsx` | See § 7. |
| `apps/mobile/__tests__/screens/LocalSignup.test.tsx` | See § 7. |
| `apps/mobile/__tests__/auth/useAppleSignIn.test.ts` | See § 7. |
| `apps/mobile/__tests__/auth/useGoogleSignIn.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// useAppleSignIn.ts
export function useAppleSignIn(): {
  signIn: () => Promise<void>;
  isLoading: boolean;
  error: AuthError | null;
  isAvailable: boolean;  // false on Android + iOS < 13
};

// useGoogleSignIn.ts
export function useGoogleSignIn(): {
  signIn: () => Promise<void>;
  isLoading: boolean;
  error: AuthError | null;
};

// useLocalAuth.ts
export function useLocalLogin(): {
  mutate: (vars: { username: string; password: string }) => void;
  isPending: boolean;
  error: AuthError | null;
};

export function useLocalSignup(): {
  mutate: (vars: {
    username: string;
    password: string;
    email?: string;
    display_name?: string;
  }) => void;
  isPending: boolean;
  error: AuthError | null;
};
```

`AuthError`:

```typescript
type AuthError =
  | { code: "username_taken"; message: string }
  | { code: "email_taken"; message: string }
  | { code: "invalid_credentials"; message: string }
  | { code: "apple_token_invalid"; message: string }
  | { code: "google_token_invalid"; message: string }
  | { code: "apple_canceled"; message: string }
  | { code: "google_canceled"; message: string }
  | { code: "network"; message: string };
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Apple button label | "Continue with Apple" | Apple's HIG; can also be "Sign in" or "Sign up." Use "Continue" since UX is unified. |
| Google button label | "Continue with Google" | Same. |
| Local password reveal | Eye icon toggles `secureTextEntry` | Standard. |
| Apple ordering | Apple button is FIRST on iOS, THIRD on Android | App Store HIG places Apple button at the top on iOS; Android prioritizes Google. |
| Form submit on Enter | Yes | iOS / Android native behavior. |
| Auto-focus username on Login mount | Yes | Reduce taps. |
| Auto-focus username on Signup mount | Yes | Same. |
| Password min length | 8 (matches BE) | Display the rule below the field. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Apple Sign-In returns canceled | No-op; surface `apple_canceled` toast only if the user previously initiated (avoid noise). |
| Apple Sign-In on Android | Hide the button entirely; show "Sign in with Apple requires iOS" inline if hidden. |
| Google Sign-In on iOS | Works via expo-auth-session. |
| BE returns `username_taken` | Toast + ribbon under the username field. |
| BE returns `invalid_credentials` | Toast "Wrong username or password." No field highlight (to avoid leaking which is wrong). |
| BE refresh fails mid-session | `AuthContext` calls `signOut()`; user lands back on AuthLanding. |
| App put to background mid-auth flow | When returning, last screen restored. No partial state leaks. |
| User signs up but then BE returns 5xx | Inline error toast; form retained. |
| Network offline | Toast "You're offline. Check your connection." No submit. |
| BE issues a JWT that we immediately decode and find corrupted | Should never happen; if it does, `clearTokens()` + error state. |
| User taps signup → username already taken → backs out → tries login with same username → works | Yes. |
| Apple returns `email=null` (subsequent sign-in) | Pass through; BE doesn't store. |
| Google returns `email_verified: false` | Pass through; BE logs INFO and accepts. |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `AuthLanding.test.tsx` | `renders_three_ctas_on_ios` | Mock platform=ios; render → 3 CTAs visible. |
| `AuthLanding.test.tsx` | `hides_apple_on_android` | platform=android → Apple button absent. |
| `AuthLanding.test.tsx` | `apple_cta_invokes_use_apple_hook` | Tap → `useAppleSignIn().signIn` called. |
| `AuthLanding.test.tsx` | `local_cta_navigates_to_local_login` | Tap → navigate to LocalLogin. |
| `LocalLogin.test.tsx` | `submit_disabled_when_fields_empty` | Empty fields → submit greyed. |
| `LocalLogin.test.tsx` | `submit_calls_use_local_login_with_payload` | Fill + submit → mutate called with username+password. |
| `LocalLogin.test.tsx` | `invalid_credentials_shows_toast` | Mock mutate to reject with `invalid_credentials` → toast visible. |
| `LocalSignup.test.tsx` | `submit_with_optional_fields_omitted_works` | Fill username+password only → mutate called without email/display_name. |
| `LocalSignup.test.tsx` | `password_short_blocks_submit_with_inline_hint` | password length 7 → submit greyed; hint visible. |
| `LocalSignup.test.tsx` | `username_taken_shows_toast` | Mutate rejects → toast. |
| `useAppleSignIn.test.ts` | `posts_identity_token_to_be` | Mock expo-apple → POST `/api/auth/apple` with token + display_name (first auth). |
| `useAppleSignIn.test.ts` | `canceled_does_not_post` | User cancels native flow → no BE call. |
| `useAppleSignIn.test.ts` | `successful_response_stores_tokens` | 201 from BE → `setTokens` called. |
| `useGoogleSignIn.test.ts` | `posts_id_token_to_be` | Mock Google → POST `/api/auth/google`. |
| `useGoogleSignIn.test.ts` | `successful_response_stores_tokens` | Same as Apple. |

**Manual QA — DARK MODE ONLY (OQ-04):**

1. Fresh install → landing screen.
2. Tap "Continue with Apple" (iOS only) → Apple modal → returns → home tab.
3. Tap "Continue with Google" → Google chooser → returns → home tab.
4. Tap "Continue with username" → login form → submit valid creds → home tab.
5. Logout (FE-009 ships it) → returns to landing.
6. Try signup with taken username → inline error + toast.
7. Kill app while logged in → relaunch → home tab (token persisted in secure-store).
8. Toggle airplane mode → submit → toast "You're offline."

Light theme out of scope (BACKLOG-001).

**Structured-log lines:** N/A on FE — all errors and successes flow through TanStack mutations.

**Failure modes:**

- BE-003/004/005 returns 5xx → toast "Something went wrong. Try again."
- expo-secure-store fails to persist → log to console (dev), toast to user, force re-auth.

## 8. Out of scope

| Item | Where |
|---|---|
| Password reset | v2. |
| Magic-link signin | v2. |
| Email verification flow | v2. |
| Account linking (Apple ↔ local) | Future ADR. |
| Light theme | BACKLOG-001. |
| "Continue as guest" | Not v1 — ADR-006 requires auth. |

## 9. Structured-log events

N/A — FE.

## 10. Rollback plan

Revert. Users can't sign in; existing tokens persist (so logged-in users keep working). Wave-3 tickets that require sign-in for first run will be visible only to already-authenticated devices.
