# BE-004 — `POST /api/auth/apple` (Sign In with Apple)

**Wave:** 1
**Type:** BE
**Blocked by:** BE-003
**Blocks:** FE-102
**ADR references:** [ADR-006 § 1.2, § 1.5, § 4.20](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

iOS users sign in with their Apple ID. The native client invokes Apple's `ASAuthorizationAppleIDProvider`, receives an Apple-signed identity token, and POSTs it to us. We validate the JWT against Apple's JWKS, extract `sub`, match or create the User, and return our own JWT pair. App Store Guideline 4.8 makes this v1-mandatory because BE-005 (Google) ships v1.

## 2. Actual solution

`app/auth/apple.py` exposes `validate_apple_identity_token(token: str) -> AppleClaims`. It:

1. Fetches Apple's JWKS from `https://appleid.apple.com/auth/keys` (HTTPS).
2. Caches the JWKS in-process for 24 h with `cachetools.TTLCache`. JWKS rotation is rare; 24 h is fine.
3. Decodes the JWT with `jose.jwt.decode` against the matching key (matched on `kid` from the unverified header), validating `iss == "https://appleid.apple.com"`, `aud == settings.apple_bundle_id`, and `exp` not in the past.
4. Returns `AppleClaims(sub, email, email_verified)`.

`POST /api/auth/apple` handler:

1. Parse `AppleSignInRequest`.
2. Call `validate_apple_identity_token(identity_token)`.
3. Run Q5 — `SELECT * FROM user WHERE auth_provider='apple' AND apple_subject_id=$1`.
4. If found: update `last_login_at`; return `AuthResponse`.
5. If not found: create a new `User` with `auth_provider='apple'`, `apple_subject_id=claims.sub`, `email=claims.email` (lowercased) if non-null, `display_name=request.display_name`, `avatar_color` from the palette. Username NULL.
6. Mint our own JWT pair (reuses `app/auth/jwt.py` from BE-003).
7. Return `AuthResponse`.

Errors:

| HTTP | error_code | When |
|---|---|---|
| 401 | `apple_token_invalid` | JWKS validation fails (bad signature, expired, wrong `aud` / `iss`). |
| 502 | `apple_jwks_unreachable` | Apple's JWKS endpoint returns 5xx or times out (10 s). |

Apple's first-auth quirk: `email` and `full_name` come back ONLY on the user's first sign-in for a given app installation. The FE passes both through; the server uses them **only when creating a new User** (i.e. on the very first match-or-create). Subsequent sign-ins ignore the optional fields per ADR-006 § 4.18.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/pyproject.toml` | Add `cachetools` and `httpx` (httpx may already be present from FastAPI's test client). |
| `services/api/app/config.py` | Add `apple_bundle_id: str`, `apple_jwks_url: str = "https://appleid.apple.com/auth/keys"`, `apple_jwks_ttl_seconds: int = 86400`. |
| `services/api/app/auth/apple.py` | `validate_apple_identity_token` + `AppleClaims` + cached `_get_jwks`. |
| `services/api/app/schemas/auth.py` | Add `AppleSignInRequest` (copy from `docs/schemas/reference/v1_pydantic.py`). |
| `services/api/app/services/user_service.py` | Add `get_or_create_apple_user(claims: AppleClaims, display_name: str \| None) -> tuple[User, bool]` (returns user + `created`). |
| `services/api/app/routes/auth.py` | Add `POST /api/auth/apple`. |
| `services/api/.env.example` | Add `APPLE_BUNDLE_ID=com.setlistpicker.app`. |
| `services/api/tests/test_auth_apple.py` | See § 7. |
| `services/api/tests/fixtures/apple_jwks.py` | Test helpers: generate a key pair, mint test identity tokens, mock Apple's JWKS endpoint. |
| `docs/CODEBASE_GUIDE.md` | Add `/api/auth/apple`. |

## 4. Method signatures / new APIs

```python
# app/schemas/auth.py
class AppleSignInRequest(_Model):
    identity_token: str
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
```

```python
# app/auth/apple.py
class AppleClaims(BaseModel):
    sub: str
    email: str | None
    email_verified: bool | None


async def validate_apple_identity_token(token: str) -> AppleClaims:
    """Validate an Apple identity token against Apple's JWKS. Returns claims.

    Raises:
        AppleTokenInvalid: signature / aud / iss / exp validation fails.
        AppleJwksUnreachable: Apple's JWKS endpoint times out or 5xx's.
    """
```

```python
# app/services/user_service.py
async def get_or_create_apple_user(
    db: AsyncSession,
    claims: AppleClaims,
    display_name: str | None,
) -> tuple[User, bool]:
    """Returns (user, created). On first-auth, populates email + display_name."""
```

Endpoint:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `POST` | `/api/auth/apple` | `AppleSignInRequest` | `AuthResponse` | 200 (existing user) / 201 (new user) |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Apple JWKS URL | `https://appleid.apple.com/auth/keys` | Apple's documented endpoint. |
| JWKS cache TTL | 24 h | JWKS rotation is rare; 24 h dramatically reduces request volume to Apple. |
| JWKS HTTP timeout | 10 s connect / 10 s read | Apple's endpoint is fast; longer mostly means an outage. |
| Apple `iss` expected | `https://appleid.apple.com` | Per Apple docs. |
| Apple `aud` expected | `settings.apple_bundle_id` | Apple ties the token to the requesting bundle id. |
| Status code on new user | 201 | Distinguishable from 200 "existing user logged in" for analytics. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Token with valid signature, wrong `aud` | 401 `apple_token_invalid` — defensive against token reuse from another app. |
| Token signed by a key not in the cached JWKS | Re-fetch the JWKS once; if still missing → 401. |
| JWKS endpoint times out | 502 `apple_jwks_unreachable`. Structured-log line `auth.apple_jwks_unreachable` at ERROR. |
| User sends `email` that conflicts with another User's email | Store the conflicting email on the new Apple user (Apple's `sub` is the unique key, not email). The email_taken constraint doesn't apply here because email-uniqueness is **per-provider** — the partial unique index on email is for the dedup case where a `local` user reuses email, not for SSO; ADR-006 § 2.1 stores Apple-relay addresses verbatim. If the email is already taken by a local user, store NULL on the Apple user and log `auth.apple_email_conflict`. |
| First sign-in with `email=None` (Apple omitted email after initial install) | Store NULL email; works. |
| Second sign-in for an existing Apple subject; FE forwards a new `display_name` | Ignored — only first-create populates these. ADR-006 § 4.20. |
| Apple sub already matches a User with `auth_provider='google'` | Not possible — partial unique indexes prevent dual-provider on one row. The query is scoped to `auth_provider='apple'` so we'd create a new User row with the same email but different provider. Acceptable (no auto-merge); this is the explicit "Identity merging is not in scope" rule in ADR-006 § 4.20. |
| Concurrent first-time Apple sign-ins for same sub | First commit wins; second hits the partial unique index on `apple_subject_id` → IntegrityError → re-run the query → return the existing row. |
| JWKS cache returns a stale key after Apple rotation | First failure causes a one-time re-fetch (`_get_jwks(force_refresh=True)`); second failure → 401. |

## 7. Acceptable validation

**Tests that MUST exist:**

| Test name | Assertion |
|---|---|
| `test_apple_signin_creates_new_user_returns_201` | Mint a valid Apple token with `sub="new-sub-1"`; POST → 201; `user.auth_provider == "apple"`; `user.apple_subject_id == "new-sub-1"`; `tokens.access_token` present. |
| `test_apple_signin_existing_subject_returns_200` | Pre-seed a User with the sub; POST → 200; same user_id. |
| `test_apple_signin_existing_subject_ignores_new_display_name` | Pre-seed `display_name="A"`; send `display_name="B"`; stored value still `"A"`. |
| `test_apple_signin_first_auth_persists_email` | First-time sub; send `email="foo@privaterelay.appleid.com"`; stored. |
| `test_apple_signin_first_auth_with_email_conflicting_local_user_stores_null` | Local user owns `"foo@bar.com"`; Apple first-auth with same email → user created with email=NULL, log line `auth.apple_email_conflict` emitted. |
| `test_apple_signin_bad_signature_returns_401` | Sign with a different key → 401 `apple_token_invalid`. |
| `test_apple_signin_wrong_aud_returns_401` | aud = a different bundle id → 401. |
| `test_apple_signin_expired_token_returns_401` | exp in the past → 401. |
| `test_apple_signin_wrong_iss_returns_401` | iss = `"https://example.com"` → 401. |
| `test_apple_jwks_timeout_returns_502` | Mock httpx to raise `TimeoutException` → 502 `apple_jwks_unreachable`. |
| `test_apple_jwks_cache_is_used` | First call fetches; second call (within TTL) does not hit httpx (verified via mock call count). |
| `test_apple_signin_updates_last_login_at_for_returning_user` | Existing user, `last_login_at` was 1 hour ago; after sign-in it's now. |
| `test_apple_concurrent_first_signin_does_not_create_duplicates` | Two concurrent POSTs with the same sub → exactly one User row; both responses succeed with same user_id. |

**Manual QA:**

1. Build a test identity token via the test fixture; curl into `localhost:8000/api/auth/apple`.
2. Confirm the user appears with `auth_provider='apple'` in psql.
3. Re-POST the same token → response shows the same `user_id`.

**Structured-log lines on success:**

| Event | Fields |
|---|---|
| `auth.apple_signin_succeeded` | `user_id`, `apple_subject_id`, `created: bool`, `request_id` |

**On failure:**

| Event | Fields |
|---|---|
| `auth.apple_token_invalid` | `reason: str` (`"bad_signature" \| "wrong_aud" \| "wrong_iss" \| "expired"`), `request_id` |
| `auth.apple_jwks_unreachable` | `error_type: str`, `error_message: str`, `request_id` |
| `auth.apple_email_conflict` | `apple_subject_id`, `attempted_email`, `existing_user_id`, `request_id` |

## 8. Out of scope

| Item | Where it lives |
|---|---|
| Linking Apple to an existing local account | Not in scope per ADR-006 § 4.20. Future ADR. |
| Apple revocation webhook (`/auth/apple/revoke`) | BACKLOG-006. |
| Native iOS client wiring | FE-102. |
| Bundle ID assignment / Apple Developer cert | Ops setup — not a code ticket. |
| Apple's private-relay forwarding | Email storage policy handled by ADR-006 § 4.18 (we store the relay as-is). |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert the PR. iOS users can no longer sign in via Apple; existing Apple-provider rows in `user` are unaffected and re-appear when the route returns. App Store builds that ship Apple Sign-In in the FE will see 404 from this endpoint until the rollback is reverted — coordinate with FE-102's rollout.
