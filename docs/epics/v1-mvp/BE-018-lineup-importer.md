# BE-018 — `scripts/import_lineup.py` + `POST /api/events/import` (admin paste-import)

**Wave:** 2
**Type:** BE
**Blocked by:** BE-002
**Blocks:** BE-013, FE-003
**ADR references:** [ADR-006 § 4.29](../../decisions/ADR-006-initial-data-schema.md), [ARCHITECTURE.md § API surface](../../ARCHITECTURE.md)

## 1. Problem statement

We need to load a festival's lineup into the database. v1 source is the `event_api_v1` adapter — JSON matching `LineupSourcePerformance` in the Pydantic reference (verified against `.local-data/tml26-w2.json`). Two entry points:

- `scripts/import_lineup.py` — CLI for local dev + ops bootstrap. Reads a file path, calls the same service code as the endpoint.
- `POST /api/events/import` — admin-token-gated paste-import for already-deployed instances.

Re-imports are idempotent on `(source_adapter, external_id)` per ADR-006 § 4.29.

## 2. Actual solution

`app/services/lineup_import_service.import_lineup(db, payload: LineupImportRequest) -> LineupImportResponse`:

1. Validate payload (Pydantic).
2. UPSERT Event on `(source_adapter, external_id)`. If new → INSERT; if existing → UPDATE (name, start_date, end_date, timezone, location).
3. For each performance:
   a. UPSERT Stage on `(event_id, external_id=performance.stage.id)`. If new → set `display_order = current_max + 10`; if existing → leave order alone.
   b. UPSERT Set on `(event_id, external_id=performance.id)`. Parse `startTime` / `endTime` strings as `TIMESTAMPTZ`.
   c. For each artist:
      i. Normalize name → `name_normalized`.
      ii. UPSERT Artist on `name_normalized` per ADR-006 § 4.29 trust-latest-non-null:
          - new: INSERT.
          - existing: UPDATE `spotify_artist_id` if payload non-null; UPDATE `image_url` if payload non-null; MERGE `social_links` (payload's non-null fields override).
      iii. UPSERT `artist_source_ref` on `(source_adapter, external_id=performance.artist.id)`.
      iv. UPSERT `set_artist` on `(set_id, artist_id)` with `position`.
4. Track counts; return `LineupImportResponse`.

All upserts in **one transaction**. Failure rolls back the entire import.

CLI:

```bash
uv run python scripts/import_lineup.py \
  --file .local-data/tml26-w2.json \
  --event-name "Tomorrowland 2026 W2" \
  --start-date 2026-07-24 \
  --end-date 2026-07-26 \
  --timezone Europe/Brussels \
  --location "Boom, Belgium" \
  --source-adapter event_api_v1 \
  --external-id tml-2026-w2
```

Admin endpoint:

```
POST /api/events/import
Headers: X-Admin-Token: $ADMIN_TOKEN
Body: LineupImportRequest
```

Returns `LineupImportResponse` with counts.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/lineup_import_service.py` | Core algorithm. |
| `services/api/app/services/artist_normalize.py` | `normalize(name) -> str` (lower + NFKD + strip diacritics + collapse whitespace). |
| `services/api/app/schemas/lineup.py` | `LineupSourceArtist`, `LineupSourceStage`, `LineupSourcePerformance`, `LineupImportRequest`, `LineupImportResponse`. |
| `services/api/app/routes/events.py` | Add `POST /api/events/import`. |
| `services/api/app/auth/admin.py` | `current_admin` dependency — checks `X-Admin-Token` against `settings.admin_token` (constant-time compare via `secrets.compare_digest`). |
| `services/api/scripts/__init__.py` | Empty. |
| `services/api/scripts/import_lineup.py` | CLI wrapper using `argparse`. |
| `services/api/tests/test_lineup_import.py` | See § 7. |
| `services/api/tests/test_artist_normalize.py` | See § 7. |
| `services/api/tests/test_admin_auth.py` | See § 7. |
| `services/api/tests/fixtures/tml_sample.json` | A 5-set fixture extracted from `tml26-w2.json` (full file is gitignored). |
| `docs/CODEBASE_GUIDE.md` | Add the CLI + endpoint. |

## 4. Method signatures / new APIs

```python
# app/services/artist_normalize.py
def normalize(name: str) -> str:
    """lower → NFKD → strip diacritics → collapse whitespace → strip."""
```

```python
# app/services/lineup_import_service.py
async def import_lineup(
    db: AsyncSession,
    payload: LineupImportRequest,
) -> LineupImportResponse: ...
```

```python
# app/auth/admin.py
async def current_admin(
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None: ...
```

Endpoint:

| Method | Path | Headers | Body | Response | Status |
|---|---|---|---|---|---|
| `POST` | `/api/events/import` | `X-Admin-Token` | `LineupImportRequest` | `LineupImportResponse` | 200 |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 401 | `admin_token_invalid` | Missing or wrong admin token. |
| 422 | (Pydantic) | Payload validation. |
| 500 | `lineup_import_failed` | Any service-layer exception; transaction rolled back. |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| `display_order` increment | 10 | Lets ops insert stages between existing ones without renumbering. |
| Constant-time admin compare | `secrets.compare_digest` | Avoid timing leaks. |
| Single transaction for import | yes | Atomic — partial imports are confusing. |
| Per-performance error handling | None — fail the batch | Encourages clean upstream payloads. |
| `name_normalized` recipe | `lower → NFKD → strip diacritics (Unicode Category Mn) → collapse whitespace via regex \s+ → strip` | ADR-006 § 4.3. |
| Source adapter literal | `Literal["event_api_v1", "manual"]` | ADR-006 § 4.8. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Re-import of the same event with identical payload | All counts in response are `_updated == n`, `_created == 0`. No churn. |
| Re-import with one artist's Spotify ID removed (regression) | Existing Spotify ID retained per § 4.29. Test asserts. |
| Re-import with one artist's Spotify ID changed | New value wins. Test asserts. |
| Re-import with new stages added | INSERT'd; `display_order = current_max + 10`. |
| Re-import with stages removed | **Not handled** — they stay (orphaned sets stay too). v1 is additive; cleanup is BACKLOG-016. Document in EPIC. |
| Performance with empty artists list | Pydantic `min_length=1` → 422. |
| Performance with `startTime` malformed | 422 — `startTime` parsed via `datetime.fromisoformat` (Python 3.12 handles the `YYYY-MM-DD HH:MM:SS+HH:MM` format). |
| Performance with `+1s` end time quirk | Stored verbatim per ADR-006 § 4.2. |
| Performance straddling midnight | Stored verbatim. |
| Two artists in payload with the same `name_normalized` but distinct source IDs | Upsert resolves to ONE Artist row; `artist_source_ref` gets two entries. Position is preserved per `set_artist`. |
| Performance with `day` mismatching the `date` (e.g. `day=FRIDAY`, `date=2026-07-26 (Sunday)`) | Stored verbatim — source is authoritative for `day_label`. ADR-006 § 4.2. |
| Bad admin token | 401 + log `auth.admin_token_invalid` at WARNING. |
| Missing admin token | 401. |
| Concurrent imports of same event | Transaction-level isolation; second import waits then merges idempotently. |
| Import file > 10 MB | Acceptable — TML W2 is < 200 KB. No size cap. |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `tests/test_artist_normalize.py` | `test_normalize_lowercases` | `normalize("EFFIN") == "effin"`. |
| `tests/test_artist_normalize.py` | `test_normalize_strips_diacritics` | `normalize("Beyoncé") == "beyonce"`. |
| `tests/test_artist_normalize.py` | `test_normalize_collapses_whitespace` | `normalize("  Close   Friends   Only  ") == "close friends only"`. |
| `tests/test_artist_normalize.py` | `test_normalize_unicode_nfkd` | `normalize("ﬁve") == "five"` (ligature → letters). |
| `tests/test_admin_auth.py` | `test_admin_token_present_passes` | Correct `X-Admin-Token` → no exception. |
| `tests/test_admin_auth.py` | `test_admin_token_missing_returns_401` | No header → 401. |
| `tests/test_admin_auth.py` | `test_admin_token_wrong_returns_401` | Bad header → 401. |
| `tests/test_lineup_import.py` | `test_import_creates_event_stages_sets_artists` | Fresh DB + 5-set fixture → 1 event, N stages, 5 sets, M artists. |
| `tests/test_lineup_import.py` | `test_reimport_idempotent_returns_updated_counts` | Same payload twice → second response has `events_created=0, sets_created=0, ...` and matching `_updated` counts. |
| `tests/test_lineup_import.py` | `test_reimport_preserves_existing_spotify_id_when_payload_null` | Seed artist with spotify_id="X"; re-import with spotify=null → DB still has "X"; counts log. |
| `tests/test_lineup_import.py` | `test_reimport_updates_spotify_id_when_payload_non_null` | Seed spotify_id="X"; re-import with spotify="Y" → DB has "Y". |
| `tests/test_lineup_import.py` | `test_reimport_merges_social_links` | Seed `{"spotify": "X"}`; re-import `{"instagram": "Y"}` → DB has `{"spotify": "X", "instagram": "Y"}`. |
| `tests/test_lineup_import.py` | `test_b2b_artists_one_set_two_artist_rows` | Set with 2 artists → 2 set_artist rows, position 0 and 1. |
| `tests/test_lineup_import.py` | `test_artist_name_collision_dedups_by_normalized` | Two payload artists with names "Effin" and "EFFIN" → 1 Artist row. |
| `tests/test_lineup_import.py` | `test_midnight_straddle_preserved` | Set 23:30–01:00 stored verbatim. |
| `tests/test_lineup_import.py` | `test_import_failure_rolls_back` | Inject a `IntegrityError` mid-loop; assert no Event row exists; assert log line `lineup.import_failed`. |
| `tests/test_lineup_import.py` | `test_import_endpoint_requires_admin_token` | 401 without header. |
| `tests/test_lineup_import.py` | `test_cli_invokes_service_with_parsed_args` | Mock `import_lineup`; assert called with payload matching args. |

**Manual QA:**

1. `uv run python scripts/import_lineup.py --file tests/fixtures/tml_sample.json ...` → CLI exits 0 with counts.
2. `psql ... -c "select count(*) from set"` → matches.
3. Re-run with the same args → counts shift to `_updated`.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `lineup.import_started` | `source_adapter`, `event_name`, `performances_count`, `request_id` |
| `lineup.import_complete` | `event_id`, `counts: dict`, `duration_ms`, `request_id` |
| `lineup.import_failed` | `source_adapter`, `external_id`, `exception_type`, `request_id` (ERROR, with traceback via `logger.exception`) |
| `lineup.artist_spotify_id_changed` | `artist_id`, `old`, `new`, `request_id` |
| `lineup.artist_spotify_id_preserved` | `artist_id`, `request_id` (when payload null but existing non-null) |
| `lineup.stage_orphaned` | `stage_id`, `request_id` (WARNING — when a stage no longer appears in re-import; v1 doesn't remove it) |

## 8. Out of scope

| Item | Where |
|---|---|
| Lineup audit row | ADR-006 § 5.4 — additive migration later. |
| Stage / set removal on re-import | BACKLOG-016. |
| Multiple source adapters per event | `event.source_adapter` is single-valued per ADR-006 § 2.4. |
| Setlist data | Out — sets are intentions, not actual played setlists. |
| Image upload (artist photos) | BE-019 fetches from Spotify. Lineup payloads carry URLs verbatim. |
| Cron-driven import refresh | Manual for v1. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert the PR. Existing imported data unaffected; future imports unavailable. Coordinate with the ops cycle.
