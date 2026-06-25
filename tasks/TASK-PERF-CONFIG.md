# TASK-SETLIST-PERF-CONFIG — Connection pool + gzip + lineup ETag

## Status

- [x] Ready

## Owner
TBD on pickup.

## Repo + branch

**Repo:** `setlist-picker`
**Branch:** `feat/perf-config-headroom` off `design/initial-schema`

## Dependencies

None — config and middleware additions only. Can ship in parallel with byb PERF tickets.

## Scope

Three config-only changes that give the festival-day architecture immediate headroom: triple the asyncpg connection pool to handle pick-write burst load, add `GzipMiddleware` to compress lineup payload over festival 4G, add ETag header on the lineup endpoint so re-fetches return 304. Out of scope: any code logic change, any schema migration, any new endpoint.

## Files to touch

| File | Purpose |
|---|---|
| `services/api/app/db/session.py` (or wherever the async engine is created — verify with grep `create_async_engine`) | Bump `pool_size` from 5 to 10, `max_overflow` from 15 to 40. Total pool: 50. Keep `pool_pre_ping=True` if present. |
| `services/api/app/main.py` | Add `GzipMiddleware` (from `starlette.middleware.gzip`) with `minimum_size=500` so small responses aren't compressed unnecessarily. |
| `services/api/app/routes/events.py` (or wherever the lineup endpoint is — verify with grep `/lineup`) | Compute `ETag` header on the response: `hashlib.sha256(str(event.updated_at).encode()).hexdigest()[:16]`. Check `If-None-Match` request header; if matches, return 304 with empty body. |
| `services/api/tests/test_lineup_etag.py` (new) | Test 200 on first request, 304 on second request with matching `If-None-Match`, 200 again after `event.updated_at` changes. |
| `services/api/tests/test_config_pool.py` (new — optional, hard to test without integration setup) | Assert engine pool_size == 10 and max_overflow == 40 at startup. |
| `docs/CODEBASE_GUIDE.md` | One-line update referencing the new pool size + gzip + ETag pattern. |

## Acceptance criteria

- [ ] `services/api/app/db/session.py` engine configured with `pool_size=10, max_overflow=40` (verify by running `python -c "from app.db.session import engine; print(engine.pool.size(), engine.pool.overflow())"` or via test).
- [ ] `GET /api/events/{id}/lineup` response headers include `Content-Encoding: gzip` when the response body is > 500 bytes AND the client sent `Accept-Encoding: gzip`.
- [ ] `GET /api/events/{id}/lineup` response headers include `ETag: "<16-char-hash>"`.
- [ ] `GET /api/events/{id}/lineup` with `If-None-Match: "<same-etag>"` returns HTTP **304 Not Modified** with empty body.
- [ ] `pytest`, `ruff check`, `mypy --strict` green.
- [ ] `docs/CODEBASE_GUIDE.md` updated.

## Tests required

- `tests/test_lineup_etag.py::test_first_request_returns_200_with_etag`
- `tests/test_lineup_etag.py::test_matching_if_none_match_returns_304`
- `tests/test_lineup_etag.py::test_etag_changes_after_event_updated_at_changes`
- `tests/test_gzip_middleware.py::test_large_response_is_gzipped` — optional but recommended; verify `Content-Encoding: gzip` on a response over 500 bytes.

## Hard rules

- snake_case JSON unchanged.
- Don't add `Cache-Control: max-age=...` to the lineup endpoint — the FE's `staleTime: Infinity` plus our ETag is sufficient; browser/RN caching of mutable content is risky.
- `GzipMiddleware.minimum_size=500` — DON'T compress small auth/health responses; the CPU overhead exceeds the bandwidth savings.
- Don't bump the pool to 100+ — the underlying Render Postgres connection limit on the current plan is the next ceiling (varies by plan; check before bumping further).

## Effort estimate

`XS` — ≤1 hour. Three small config changes plus tests.

## Risk

**Low.** Config-only. Rollback is reverting the three diffs.

## Notes

- `GzipMiddleware` MUST be added before any other middleware that modifies the response body (auth, CORS).
- The pool bump (5+15 → 10+40) gives ~833 picks/sec headroom at 5 round-trips per write. Verify Render Postgres connection limit isn't exceeded: `SHOW max_connections` against the dev DB.
- ETag format: `'"<hash>"'` — note the surrounding double-quotes per HTTP spec.

## Definition of done

- [ ] All acceptance criteria checked.
- [ ] Tests green.
- [ ] Feature branch pushed + fast-forward merged into `design/initial-schema`.
- [ ] Render auto-deploys; smoke `curl -I https://setlist-picker-dev.onrender.com/api/events/<id>/lineup` shows ETag and Content-Encoding: gzip.
- [ ] `docs/CODEBASE_GUIDE.md` updated.
- [ ] Report posted to Dispatch with final commit SHA + smoke output.
