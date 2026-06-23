# BE-003 — Local auth: signup, login, refresh, /me, JWT middleware

**Wave:** 1
**Type:** BE
**Blocked by:** BE-002
**Blocks:** BE-004, BE-005, BE-006, BE-007, BE-008, BE-009, BE-010
**ADR references:** [ADR-006 § 1, § 4.16, § 4.17, § 4.18, § 4.19](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

Every non-`/auth/*` endpoint requires `Authorization: Bearer <jwt>`. We need the `local` auth provider — `username + password + optional email` signup, login, and refresh — plus the JWT dependency that every later endpoint hangs off. Apple (BE-004) and Google (BE-005) reuse the same JWT machinery and the same User table; they just bypass the password step.

## 2. Actual solution

`app/auth/` holds the auth layer.

- `app/auth/hashing.py` — `hash_password(plain) -> str`, `verify_password(plain, encoded) -> bool` using `argon2-cffi` with `m=65536, t=3, p=4`.
- `app/auth/jwt.py` — `encode_access(user_id) -> str`, `encode_refresh(user_id) -> tuple[str, UUID]` (returns `jti`), `decode(token, expected_type) -> Claims`. `JWT_SECRET` read from `Settings`. Claims are a Pydantic model — `sub`, `iat`, `exp`, `type`, `jti?`.
- `app/auth/dependencies.py` — `current_user` FastAPI dependency. Reads `Authorization` header, decodes via `jwt.decode(token, expected_type="access")`, loads `User` by `sub`, raises 401 on any failure (with structured-log line `auth.token_rejected`). Used by every later endpoint.
- `app/services/user_service.py` — `create_local_user(payload) -> User`, `authenticate(username, password) -> User`. The service lowercases `username` + `email` on write per ADR-006 § 4.16; comparisons run `LOWER() = LOWER()` on both sides as defense-in-depth (the partial UNIQUE index in BE-002 trusts the app).
- `app/routes/auth.py` — three routes: `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/refresh`.
- `app/routes/users.py` — two routes: `GET /api/users/me`, `PATCH /api/users/me`.

Avatar color at signup: server picks from a 12-color palette (deterministic — `palette[hash(user_id) % 12]`). FE-009 lets the user change it later.

Bare `except Exception` is forbidden (NF-005). Specific catches: `argon2.exceptions.VerifyMismatchError`, `sqlalchemy.exc.IntegrityError`, `jose.JWTError` (or whichever JWT library — see § 5).

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/pyproject.toml` | Add `argon2-cffi`, `python-jose[cryptography]` (HS256 sufficient — no asymmetric in v1). |
| `services/api/app/config.py` | Add `jwt_secret: SecretStr`, `jwt_access_ttl_hours: int = 24`, `jwt_refresh_ttl_days: int = 7`. |
| `services/api/app/auth/__init__.py` | Re-exports. |
| `services/api/app/auth/hashing.py` | Argon2id wrappers. |
| `services/api/app/auth/jwt.py` | Encode + decode + Claims model. |
| `services/api/app/auth/dependencies.py` | `current_user` dep. |
| `services/api/app/auth/palette.py` | The 12-color avatar palette constant. |
| `services/api/app/services/user_service.py` | Service layer. |
| `services/api/app/schemas/auth.py` | Pydantic shapes copied from `docs/schemas/reference/v1_pydantic.py` § Auth. |
| `services/api/app/schemas/users.py` | `UserOut`, `UserUpdate`. |
| `services/api/app/routes/auth.py` | Signup / login / refresh. |
| `services/api/app/routes/users.py` | `/users/me` (GET + PATCH). |
| `services/api/app/main.py` | Include the two routers. |
| `services/api/.env.example` | Add `JWT_SECRET=replace-with-32-byte-secret`. |
| `services/api/tests/test_auth_signup.py` | See § 7. |
| `services/api/tests/test_auth_login.py` | See § 7. |
| `services/api/tests/test_auth_refresh.py` | See § 7. |
| `services/api/tests/test_users_me.py` | See § 7. |
| `services/api/tests/test_jwt_dependency.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add `/api/auth/*` and `/api/users/me` entries. |

## 4. Method signatures / new APIs

```python
# app/schemas/auth.py — verbatim from docs/schemas/reference/v1_pydantic.py
class UserCreate(_Model):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=80)


class UserLogin(_Model):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class TokenPair(_Model):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime


class AuthResponse(_Model):
    user: UserOut
    tokens: TokenPair


class TokenRefreshRequest(_Model):
    refresh_token: str
```

```python
# app/auth/jwt.py
class Claims(BaseModel):
    sub: str
    iat: int
    exp: int
    type: Literal["access", "refresh"]
    jti: str | None = None


def encode_access(user_id: UUID) -> tuple[str, datetime]: ...
def encode_refresh(user_id: UUID) -> tuple[str, datetime, UUID]: ...  # token, exp, jti
def decode(token: str, expected_type: Literal["access", "refresh"]) -> Claims: ...
```

```python
# app/auth/dependencies.py
async def current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User: ...
# Raises HTTPException(401, error_code="invalid_token") on any failure.
```

Endpoints:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `POST` | `/api/auth/signup` | `UserCreate` | `AuthResponse` | 201 |
| `POST` | `/api/auth/login` | `UserLogin` | `AuthResponse` | 200 |
| `POST` | `/api/auth/refresh` | `TokenRefreshRequest` | `TokenPair` | 200 |
| `GET`  | `/api/users/me` | — | `UserOut` | 200 |
| `PATCH` | `/api/users/me` | `UserUpdate` | `UserOut` | 200 |

Error responses (all use `ErrorResponse` shape from the Pydantic reference):

| HTTP | error_code | When |
|---|---|---|
| 400 | `username_taken` | Signup hits the partial unique index on `username`. |
| 400 | `email_taken` | Signup hits the partial unique index on `email`. |
| 401 | `invalid_credentials` | Login: no matching user OR password verify fails. |
| 401 | `invalid_token` | Any decode failure (expired, wrong signature, wrong `type`). |
| 401 | `user_not_found` | Token valid but user row deleted. |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Argon2 params | `m=65536` (64 MiB), `t=3`, `p=4` | OWASP 2024 — ADR-006 § 4.17. |
| Access token TTL | 24 h | ADR-006 § 4.19. |
| Refresh token TTL | 7 d | ADR-006 § 4.19. |
| JWT alg | `HS256` | ADR-006 § 4.19. |
| Password min length | 8 | NIST-acceptable; allows passphrase-style choices. |
| Password max length | 128 | Argon2 truncates at 2^32 bytes; 128 keeps memory cost bounded. |
| Username regex | `^[A-Za-z0-9_-]{3,32}$` | ADR-006 § 2.1. Server lowercases before write. |
| Avatar palette length | 12 colors | Matches the friends-list-spec palette. Stored as constant in `app/auth/palette.py`. |
| Login-fail constant-time | yes | `verify_password` runs on a known-bad hash if user-not-found to avoid timing leaks. |
| JWT library | `python-jose` | Mature, mypy-friendly, supports HS256. |

The 12 avatar colors (chosen against the Cosmic-Neon dark backdrop, WCAG AA contrast at large text):

```python
AVATAR_PALETTE: list[str] = [
    "#a78bfa",  # cosmic violet
    "#36c6ff",  # cyan
    "#ff4f9a",  # hot pink
    "#2dd4bf",  # teal
    "#ffd23f",  # amber
    "#ff6a3d",  # vermilion
    "#a06bff",  # purple
    "#28e0ff",  # bright cyan
    "#f5d90a",  # yellow
    "#7bdcb5",  # mint
    "#ff8ad6",  # blush pink
    "#cdb4fe",  # lilac
]
```

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Signup with `username="Jerome"` | Server lowercases to `"jerome"` and stores it. UserOut returns `"jerome"`. |
| Signup with `email="J@FOO.com"` | Lowercased to `"j@foo.com"`. Returned lowercase. |
| Signup with no `email` | `email` is NULL; account works; no password-reset path (out of scope v1). |
| Signup with `username` differing only in case from an existing user | 400 `username_taken`. Defense-in-depth `LOWER() = LOWER()` query in the service catches this even if a stray uppercase write happened pre-fix. |
| Login with `username="JEROME"` against stored `"jerome"` | `LOWER(username) = LOWER($1)` — case-insensitive match; 200. |
| Login with the right username and wrong password | 401 `invalid_credentials`. `argon2.exceptions.VerifyMismatchError` caught + logged at WARNING. |
| Login with a non-existent username | 401 `invalid_credentials`. Same response time as wrong-password (constant-time verify against a known-bad hash). |
| Refresh with an access token | 401 `invalid_token` (claims `type` mismatch). |
| Refresh with an expired refresh token | 401 `invalid_token`. |
| `/users/me` with no `Authorization` header | 401 `invalid_token` (header missing). |
| `/users/me` with malformed header (e.g. `Bearer foo bar`) | 401 `invalid_token`. |
| `/users/me` for an SSO user (apple_subject_id set, username NULL) | Returns `UserOut` with `username=None` — handled by FE. |
| PATCH `/users/me` with `email` set to a value owned by another user | 400 `email_taken`. |
| PATCH `/users/me` with `avatar_color="not-a-hex"` | Pydantic 422 validation error (pattern mismatch). |
| Two concurrent signup requests with the same username | Whichever commits first wins; the second hits `IntegrityError` → 400 `username_taken`. |
| Token issued before `JWT_SECRET` rotated | Validation fails → 401 `invalid_token`. (No v1 rotation tooling — flagged in EPIC.) |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `tests/test_auth_signup.py` | `test_signup_local_returns_201_with_user_and_tokens` | POST `/api/auth/signup` with valid body → 201; body contains `user.username == "jerome"` and `tokens.access_token` and `tokens.refresh_token`. |
| `tests/test_auth_signup.py` | `test_signup_lowercases_username` | Send `"Jerome"`, expect stored + returned `"jerome"`. |
| `tests/test_auth_signup.py` | `test_signup_lowercases_email` | Send `"J@Foo.com"`, expect `"j@foo.com"`. |
| `tests/test_auth_signup.py` | `test_signup_assigns_avatar_color_from_palette` | Returned `avatar_color` is one of `AVATAR_PALETTE`. |
| `tests/test_auth_signup.py` | `test_signup_duplicate_username_returns_400` | Second signup with same username → 400 `username_taken`. |
| `tests/test_auth_signup.py` | `test_signup_duplicate_email_returns_400` | Second signup with same email (different username) → 400 `email_taken`. |
| `tests/test_auth_signup.py` | `test_signup_case_insensitive_username_collision` | Signup `"Jerome"`, then signup `"jerome"` → 400. |
| `tests/test_auth_signup.py` | `test_signup_invalid_username_chars_returns_422` | `"jerome!"` → 422 Pydantic validation. |
| `tests/test_auth_signup.py` | `test_signup_short_password_returns_422` | 7-char password → 422. |
| `tests/test_auth_login.py` | `test_login_returns_tokens_for_correct_credentials` | 200, fresh token pair. |
| `tests/test_auth_login.py` | `test_login_uppercase_username_matches` | Send `"JEROME"` against stored `"jerome"` → 200. |
| `tests/test_auth_login.py` | `test_login_wrong_password_returns_401` | 401 `invalid_credentials`. |
| `tests/test_auth_login.py` | `test_login_nonexistent_user_returns_401` | 401 `invalid_credentials`; assert response timing within 50 ms of the wrong-password case (constant-time). |
| `tests/test_auth_login.py` | `test_login_updates_last_login_at` | `User.last_login_at` is set on success. |
| `tests/test_auth_refresh.py` | `test_refresh_returns_fresh_pair` | New `access_token` differs from input refresh; new refresh present. |
| `tests/test_auth_refresh.py` | `test_refresh_with_access_token_rejected` | Posting an access token → 401 `invalid_token`. |
| `tests/test_auth_refresh.py` | `test_refresh_expired_returns_401` | Manually-built expired token → 401. |
| `tests/test_jwt_dependency.py` | `test_current_user_with_valid_token_returns_user` | Calls a test-only protected route; user matches signup. |
| `tests/test_jwt_dependency.py` | `test_current_user_missing_header_returns_401` | No `Authorization` → 401 `invalid_token`. |
| `tests/test_jwt_dependency.py` | `test_current_user_malformed_header_returns_401` | `"foo bar"` → 401. |
| `tests/test_jwt_dependency.py` | `test_current_user_user_deleted_returns_401` | Token valid; user row deleted → 401 `user_not_found`. |
| `tests/test_users_me.py` | `test_get_users_me_returns_caller` | Auth'd GET → caller's `UserOut`. |
| `tests/test_users_me.py` | `test_patch_users_me_updates_display_name` | Send `{"display_name": "🎵 Jerome"}`; `updated_at` advances; GET reflects it. |
| `tests/test_users_me.py` | `test_patch_users_me_email_collision_returns_400` | 400 `email_taken`. |
| `tests/test_users_me.py` | `test_patch_users_me_avatar_color_invalid_returns_422` | `"red"` → 422. |

**Manual QA (curl smoke):**

1. `curl -s -X POST localhost:8000/api/auth/signup -H 'content-type: application/json' -d '{"username":"jerome","password":"correct horse"}' | jq` → 201 with token pair.
2. `curl -s localhost:8000/api/users/me -H "authorization: Bearer $TOKEN" | jq` → caller.
3. Modify the token's last char → 401 `invalid_token`.

**Structured-log lines on success:**

| Event | Fields |
|---|---|
| `auth.user_created` | `user_id`, `auth_provider="local"`, `request_id` |
| `auth.login_succeeded` | `user_id`, `auth_provider="local"`, `request_id` |
| `auth.token_refreshed` | `user_id`, `request_id` |

**Structured-log lines on failure:**

| Event | Fields |
|---|---|
| `auth.login_failed` | `username_attempted`, `reason="bad_password" \| "no_such_user"`, `request_id` (WARNING level) |
| `auth.token_rejected` | `reason="expired" \| "bad_signature" \| "wrong_type" \| "missing_header"`, `request_id` (WARNING) |

## 8. Out of scope

| Item | Where it lives |
|---|---|
| Apple Sign-In | BE-004. |
| Google Sign-In | BE-005. |
| Password change endpoint | BACKLOG-004 (out of v1). |
| Password reset / SMTP | v2 — ADR-006 § 1.5. |
| Refresh-token revocation | v2 — ADR-006 § 1.5; `jti` is included for the future table. |
| Rate-limiting on login | BACKLOG-005 — outside v1. |
| Email verification | v2. |

## 9. Structured-log events

(See § 7.) All event tags are emitted via structlog's `bound_contextvars` so `request_id` is always present.

## 10. Rollback plan

Revert the PR. The five routes disappear; the `current_user` dependency is unused. Tickets BE-004..BE-010 won't merge until this lands again, but no data has been written by users in production. If users have already signed up before rollback, their rows in `user` remain but can't authenticate until the routes return — acceptable for a pre-launch system.
