# BE-005 — `POST /api/auth/google` (Google Sign-In)

**Wave:** 1
**Type:** BE
**Blocked by:** BE-003
**Blocks:** FE-102
**ADR references:** [ADR-006 § 1.2, § 1.5, § 4.24](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

Android users (and iOS users who prefer Google) sign in with a Google account. The native client invokes Google's auth flow and POSTs the resulting ID token. We validate it against Google's JWKS, extract `sub`, match-or-create the User, return our JWT pair. Mirror of BE-004.

## 2. Actual solution

Symmetric to BE-004 with these differences:

- JWKS URL: `https://www.googleapis.com/oauth2/v3/certs`.
- Expected `iss` is one of `{"https://accounts.google.com", "accounts.google.com"}` — Google's docs list both as legitimate.
- Expected `aud` matches our Google client ID (`settings.google_client_id`).
- DB column: `user.google_subject_id` (not `apple_subject_id`).
- Service helper: `get_or_create_google_user(claims, display_name)`.

Code reuses `_jwks_cache` machinery — pull the cache helper into `app/auth/jwks.py` shared by both providers if BE-004 hasn't already.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/config.py` | Add `google_client_id: str`, `google_jwks_url: str = "https://www.googleapis.com/oauth2/v3/certs"`. |
| `services/api/app/auth/jwks.py` | Shared JWKS cache (refactor — extract from BE-004's `apple.py` if it landed first). |
| `services/api/app/auth/google.py` | `validate_google_id_token`, `GoogleClaims`. |
| `services/api/app/schemas/auth.py` | Add `GoogleSignInRequest`. |
| `services/api/app/services/user_service.py` | Add `get_or_create_google_user`. |
| `services/api/app/routes/auth.py` | Add `POST /api/auth/google`. |
| `services/api/.env.example` | Add `GOOGLE_CLIENT_ID=replace-me.apps.googleusercontent.com`. |
| `services/api/tests/test_auth_google.py` | See § 7. |
| `services/api/tests/fixtures/google_jwks.py` | Test helpers. |
| `docs/CODEBASE_GUIDE.md` | Add `/api/auth/google`. |

## 4. Method signatures / new APIs

```python
# app/schemas/auth.py
class GoogleSignInRequest(_Model):
    id_token: str
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
```

```python
# app/auth/google.py
class GoogleClaims(BaseModel):
    sub: str
    email: str | None
    email_verified: bool | None
    name: str | None  # Google sends "name" as a top-level claim; FE may or may not forward.


async def validate_google_id_token(token: str) -> GoogleClaims: ...
```

Endpoint:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `POST` | `/api/auth/google` | `GoogleSignInRequest` | `AuthResponse` | 200 / 201 |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 401 | `google_token_invalid` | Validation fails. |
| 502 | `google_jwks_unreachable` | JWKS endpoint times out / 5xx's. |

## 5. Constants and thresholds

Same as BE-004 (JWKS TTL 24 h, HTTP timeout 10 s). Differences:

| Constant | Value | Rationale |
|---|---|---|
| JWKS URL | `https://www.googleapis.com/oauth2/v3/certs` | Google docs. |
| Allowed `iss` | `{"https://accounts.google.com", "accounts.google.com"}` | Both are documented as valid. |

## 6. Edge cases enumerated

Mirror BE-004 § 6 with `google_*` substituted, plus:

| Case | Expected behavior |
|---|---|
| Token `iss == "accounts.google.com"` (no scheme) | Accepted. The `iss` validator allows both forms. |
| Google sends `name` in the claim but FE forwards a different `display_name` | Use the FE's `display_name` on first-auth (or `claims.name` if FE omitted it). |
| `email_verified=false` | Still accept — we don't gate on email verification in v1 (no password-reset flow that depends on it). Log `auth.google_email_unverified` at INFO. |
| Same email already owned by a local or Apple user | Create new Google user, store the email (no conflict because the partial unique on email is one-per-row but our service layer should check: if conflict, store NULL email + log `auth.google_email_conflict` — same pattern as Apple). |

## 7. Acceptable validation

**Tests that MUST exist (mirror BE-004):**

| Test name | Assertion |
|---|---|
| `test_google_signin_creates_new_user_returns_201` | New sub → 201; `auth_provider == "google"`. |
| `test_google_signin_existing_subject_returns_200` | Pre-seeded sub → 200. |
| `test_google_signin_accepts_both_iss_forms` | Token with `iss="accounts.google.com"` → 201; token with `iss="https://accounts.google.com"` → 201. |
| `test_google_signin_wrong_aud_returns_401` | aud mismatch → 401. |
| `test_google_signin_bad_signature_returns_401` | Signed with non-Google key → 401. |
| `test_google_signin_expired_token_returns_401` | Past exp → 401. |
| `test_google_jwks_timeout_returns_502` | Mock timeout → 502. |
| `test_google_jwks_cache_is_used` | Second call (within TTL) doesn't hit httpx. |
| `test_google_signin_email_conflict_stores_null` | Local user owns the email; Google first-auth → user has email=NULL + log line. |
| `test_google_signin_updates_last_login_at_for_returning_user` | Existing user; `last_login_at` bumped to now. |
| `test_google_signin_email_unverified_still_succeeds` | `email_verified=false` → 201 + log line `auth.google_email_unverified`. |
| `test_google_concurrent_first_signin_does_not_create_duplicates` | Two concurrent POSTs same sub → one row, both 2xx. |

**Manual QA:**

Same shape as BE-004 with a test Google token from the fixture.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `auth.google_signin_succeeded` | `user_id`, `google_subject_id`, `created: bool`, `request_id` |
| `auth.google_token_invalid` | `reason: str`, `request_id` |
| `auth.google_jwks_unreachable` | `error_type`, `error_message`, `request_id` |
| `auth.google_email_conflict` | `google_subject_id`, `attempted_email`, `existing_user_id`, `request_id` |
| `auth.google_email_unverified` | `google_subject_id`, `request_id` (INFO) |

## 8. Out of scope

Same as BE-004 § 8. Plus:

| Item | Where |
|---|---|
| Google account linking to existing local | BACKLOG-007. |
| Google Workspace `hd` claim domain filtering | Not needed for v1. |
| Google's revocation webhook | BACKLOG-008. |
| Android client setup | FE-102. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert the PR. Android sign-in stops working; users retain stored rows but can't authenticate via Google until revert. Coordinate with FE-102.
