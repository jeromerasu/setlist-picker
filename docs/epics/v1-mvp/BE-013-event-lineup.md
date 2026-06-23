# BE-013 — `GET /api/events/{event_id}/lineup` (stages + sets + artists)

**Wave:** 2
**Type:** BE
**Blocked by:** BE-002
**Blocks:** FE-005, FE-006, FE-007, BE-017
**ADR references:** [ADR-006 § 2.5, § 2.6, § 2.7, § 2.9, § 4.29](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

The schedule view (FE-006) needs the full lineup for an event — every stage, every set, every artist on each set. One request. Read-only.

## 2. Actual solution

`app/services/event_service.get_event_lineup(db, event_id) -> EventLineupResponse`.

Algorithm:

1. SELECT event by `event_id`. If missing → 404.
2. SELECT all stages for the event, ORDER BY `display_order ASC, name ASC`.
3. SELECT all sets for the event, eager-load `set_artists → artist` via SQLAlchemy `selectinload`. ORDER BY `starts_at ASC`.
4. Build `EventLineupResponse`.

`selectinload` two-step query avoids N+1. The total payload is bounded: TML 2026 W2 has 405 performances × ~1 artist on average — ≈ 50 KB JSON. Acceptable for a one-shot fetch the FE caches in expo-sqlite.

Authenticated. Same reasoning as BE-012.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/event_service.py` | Add `get_event_lineup`. |
| `services/api/app/schemas/events.py` | `EventLineupResponse`, `StageDetail`, `SetDetail`, `ArtistRef`, `SocialLinks` (copy from reference). |
| `services/api/app/routes/events.py` | Add `GET /api/events/{event_id}/lineup`. |
| `services/api/tests/test_event_lineup.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add the endpoint. |

## 4. Method signatures / new APIs

(Already in `docs/schemas/reference/v1_pydantic.py` — `EventLineupResponse`, `StageDetail`, `SetDetail`, `ArtistRef`.)

Endpoint:

| Method | Path | Response | Status |
|---|---|---|---|
| `GET` | `/api/events/{event_id}/lineup` | `EventLineupResponse` | 200 / 404 |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 404 | `event_not_found` | Event missing. |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Stage ordering | `display_order ASC, name ASC` | UI deterministic. |
| Set ordering | `starts_at ASC, display_name ASC` | Calendar deterministic. |
| Set-artist ordering | by `set_artist.position ASC` | ADR-006 § 4.4. |
| Response size budget | 200 KB | TML W2 reference fixture serializes < 100 KB; 2× headroom. Log if exceeded. |
| N+1 prevention | `selectinload(Set.artists)` and `selectinload(Set.stage)` | Verified by test asserting query count. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Event with zero stages or sets | 200; empty arrays. |
| Set without any artists | Shouldn't happen — `set_artist` has min_length=1 in import per [`LineupSourcePerformance`](../../schemas/reference/v1_pydantic.py). Service treats as bug — 500 + log `event.set_without_artists` (defensive only). |
| Set straddling midnight (TML quirk) | `starts_at` < `ends_at` even across day boundary; FE handles rendering. |
| Set with the `+1s` quirk (TML) | Returned verbatim per ADR-006 § 4.2. |
| Artist with NULL `spotify_artist_id` (no Spotify mapping) | `spotify_artist_id: null` in response. FE handles. |
| Artist with `social_links` JSON | Returned verbatim. |
| Event with 1000+ sets | Slow query; acceptable for v1 (TML W2 has 405). Log `event.lineup_size_exceeded_budget` if response > 200 KB. |
| Caller unauthenticated | 401. |

## 7. Acceptable validation

**Tests that MUST exist:**

| Test name | Assertion |
|---|---|
| `test_get_lineup_returns_event_summary_stages_sets` | Seed event + 2 stages + 3 sets; response has matching counts. |
| `test_get_lineup_orders_stages_by_display_order` | Stages with `display_order` 2, 1, 3 → returned in order 1, 2, 3. |
| `test_get_lineup_orders_sets_by_starts_at` | Sets seeded out of order → response sorted ascending. |
| `test_get_lineup_includes_artists_per_set` | Set with 3 artists → 3 entries in `set.artists`, sorted by `position`. |
| `test_get_lineup_no_n_plus_1` | Use SQLAlchemy event listener to count queries; 100 sets × 3 artists each → ≤ 3 queries total. |
| `test_get_lineup_missing_event_returns_404` | Random UUID → 404. |
| `test_get_lineup_handles_midnight_straddle` | Set with starts_at=23:00, ends_at=01:00 next day → returned verbatim. |
| `test_get_lineup_unauthenticated_returns_401` | No header → 401. |

**Manual QA:**

After BE-018's `import_lineup.py` seeds an event from `.local-data/tml26-w2.json`:

1. `curl -H "authorization: Bearer $TOKEN" /api/events/$EVT/lineup | jq '.stages | length'` → 15 (TML W2 stages).
2. `... | jq '.sets | length'` → 405.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `event.lineup_served` | `event_id`, `stage_count`, `set_count`, `bytes`, `request_id` (DEBUG) |
| `event.lineup_size_exceeded_budget` | `event_id`, `bytes`, `request_id` (WARNING) |

## 8. Out of scope

| Item | Where |
|---|---|
| Pagination | Not v1 — payload size bounded. |
| Filtering by stage / day | FE-side per [calendar-spec](../../features/calendar-spec.md). |
| Gzip transport compression | Render does this at the edge. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. Schedule screen breaks on cold load (no cached payload). Restore by re-merging.
