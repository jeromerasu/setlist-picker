# Wave 1 BE — Overnight Status (2026-06-23)

## Completed this session

| Ticket | Commit | Summary |
|--------|--------|---------|
| BE-001 | ef4575f | FastAPI scaffold: uv + structlog + ruff + mypy --strict + pytest-asyncio session-scoped |
| BE-002 | abf8aa9 | V001 Alembic migration: 13 tables + 27 indexes per ADR-006; 9 smoke tests + idempotency test |
| BE-003 | bbf7a6e | Local auth: signup / login / refresh / GET+PATCH /me; JWT HS256; argon2-cffi hashing; 25 tests |
| BE-004 | 1f33ea3 | Sign In with Apple: RS256 JWKS cache (cachetools TTL); `get_or_create_apple_user`; 13 tests |
| BE-005 | 99d5db8 | Google Sign-In: shared JWKS infrastructure; both `iss` forms; `get_or_create_google_user`; 14 tests |

All 5 tickets pushed to `design/initial-schema` (PR #2 auto-updated).

## Final test run

```
66 passed in 5.38s
```

ruff ✓ · ruff format ✓ · mypy --strict ✓ · pytest ✓

## Key decisions made

- **`client` fixture injects `db_session` via `get_db` override** — gives full transactional rollback isolation for HTTP tests without needing a separate test DB per test.
- **`begin_nested()` instead of `db.rollback()`** in service layer (`create_local_user`, `patch_user`) — uses SAVEPOINT so IntegrityError handling doesn't tear down the outer test transaction.
- **Mock patch target is the usage site** (`app.auth.apple.fetch_jwks`, `app.auth.google.fetch_jwks`), not the definition site (`app.auth.jwks.fetch_jwks`) — because the name is bound at import time.
- **Google + Apple infrastructure landed together in BE-004** commit; BE-005 is the Google test coverage commit.

## Next: Wave 1 BE (remaining tickets)

BE-006 onwards per the v1-mvp epic. Wave 1 foundation is complete.
