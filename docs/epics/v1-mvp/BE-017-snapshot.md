# BE-017 — `GET /api/groups/{invite_code}/snapshot` (screenshotable "where will we be" view)

**Wave:** 2
**Type:** BE
**Blocked by:** BE-009, BE-013
**Blocks:** FE-008
**ADR references:** [ADR-006 § 3.1 Q2, § 4.13, § 4.14](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

The "Right Now" view (FE-008) lets a user screenshot "where will the group be at time T" and share it. The endpoint returns a self-contained per-stage breakdown of sets in `[at, at + window_minutes]` with every member's active picks denormalized — display names + avatar colors baked in so a single screen capture is intelligible without further lookups.

## 2. Actual solution

`app/services/snapshot_service.get_snapshot(db, caller, group, at: datetime, window_minutes: int) -> GroupSnapshotResponse`.

Runs Q2 from ADR-006 § 3.1 — single query joining `set → stage → pick → member → user` filtered to the group's event. Returns:

- Top-level: `group_id`, `invite_code`, `group_name`, `event_id`, `event_name`, `timezone`, `snapshot_at`, `window_minutes`, `members_total`.
- Per stage (ordered by `display_order`): `stage_id`, `name`, `display_order`, `sets[]`.
- Per set (ordered by `starts_at`): `set_id`, `display_name`, `artist_names: list[str]`, `day_label`, `starts_at`, `ends_at`, `pickers: list[SnapshotMember]`.
- Per picker: `user_id`, `member_id`, `display_name` (resolved via COALESCE), `avatar_color`.

`members_total` = count of all members in the group (not just members with picks in the window).

Same `Last-Modified` / `If-Modified-Since` / 304 dance as BE-009. The 30-second cadence comes from the FE per ADR-006 § 4.14.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/snapshot_service.py` | New file. |
| `services/api/app/schemas/snapshot.py` | `SnapshotMember`, `SnapshotSet`, `SnapshotStage`, `GroupSnapshotResponse`. |
| `services/api/app/routes/groups.py` | Add `GET /api/groups/{invite_code}/snapshot`. |
| `services/api/tests/test_snapshot.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add the endpoint. |

## 4. Method signatures / new APIs

(Already in `docs/schemas/reference/v1_pydantic.py`.)

Endpoint:

| Method | Path | Query | Response | Status |
|---|---|---|---|---|
| `GET` | `/api/groups/{invite_code}/snapshot` | `?at=<ISO-8601>&window_minutes=<int>` | `GroupSnapshotResponse` | 200 / 304 / 400 / 404 / 403 |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 400 | `at_required` | `at` query param missing. |
| 400 | `window_minutes_out_of_range` | `window_minutes < 5` or `> 360`. |
| 404 | `group_not_found` | — |
| 403 | `not_a_member` | — |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| `window_minutes` min | 5 | Below this, a set entirely contained in the window is unusual; the snapshot is uninformative. |
| `window_minutes` max | 360 | 6 hours. Beyond this, the snapshot is "the whole evening" and is no longer a "right now" view. |
| `window_minutes` default | 60 | Matches the task brief's `?at=&window_minutes=60` example. |
| Inclusion rule | `starts_at < at + window AND ends_at > at` | Overlap. ADR-006 § 3.1 Q2 SQL. |
| Stage ordering | `display_order ASC` | Layout-deterministic across captures. |
| Set ordering within stage | `starts_at ASC` | Same. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| `at` outside the event's start/end window | Returns 200 with empty `stages[].sets` — no sets overlap. `members_total` still populated. FE renders "No sets at this time." |
| `at` lands exactly on a set's `ends_at` | Excluded per `ends_at > at` strict-inequality. |
| `at` lands exactly on a set's `starts_at` | Included. |
| Set straddling midnight | Included if window overlaps either side. |
| Group has no picks in the window | Each set's `pickers` is empty; `members_total` non-zero. |
| Group has one member who picked many sets across the window | All their picks present. |
| Set with multiple artists | `artist_names` is the full list, source-ordered (per `set_artist.position`). |
| Caller not a Member of the group | 403 `not_a_member`. |
| `at` malformed (not ISO-8601) | 422 Pydantic. |
| `at` in the past relative to server | Still works — no temporal filtering. Useful for sharing "what we did last night." |
| `window_minutes=0` | 422 (`ge=5`). |
| `window_minutes=361` | 422 (`le=360`). |
| Group's event lacks any stages or sets | 200 with `stages: []`. |

## 7. Acceptable validation

**Tests that MUST exist:**

| Test name | Assertion |
|---|---|
| `test_snapshot_returns_sets_overlapping_window` | Seed 4 sets: 2 in window, 1 before, 1 after; response includes the 2. |
| `test_snapshot_ordering_stage_display_then_starts_at` | Seed stages out of order + sets out of order; response is deterministic. |
| `test_snapshot_pickers_denormalized` | Member A picks a set; response includes A's `display_name`, `avatar_color`, `user_id`, `member_id` denormalized. |
| `test_snapshot_resolves_display_name_via_coalesce` | Member with override → snapshot uses override; without override → user.display_name; neither → username. |
| `test_snapshot_members_total_counts_all_group_members` | 5 members in group, 2 with picks in window → `members_total == 5`. |
| `test_snapshot_no_overlap_returns_empty_sets` | `at` outside event window → `stages[].sets == []`. |
| `test_snapshot_starts_at_equal_at_is_included` | Set starts_at == at → present. |
| `test_snapshot_ends_at_equal_at_is_excluded` | Set ends_at == at → absent. |
| `test_snapshot_missing_at_returns_400` | No `at` query param → 400 `at_required`. |
| `test_snapshot_window_too_small_returns_422` | `window_minutes=4` → 422. |
| `test_snapshot_window_too_large_returns_422` | `window_minutes=361` → 422. |
| `test_snapshot_window_default_60` | Omit `window_minutes` → uses 60. |
| `test_snapshot_not_a_member_returns_403` | Auth'd non-member → 403. |
| `test_snapshot_unknown_code_returns_404` | Random code → 404. |
| `test_snapshot_if_modified_since_returns_304` | First call → capture `Last-Modified`; second call with that header → 304. |
| `test_snapshot_after_new_pick_returns_200` | Cache, then a new pick lands; next call with old `If-Modified-Since` → 200 with the updated picker. |
| `test_snapshot_no_n_plus_1` | 50-set, 10-member group → ≤ 3 queries (the SELECT, the members-count SELECT, optional event SELECT). |

**Manual QA:**

1. Seed a group with 3 members, 5 sets, 3 active picks.
2. `curl ".../snapshot?at=2026-09-25T22:00:00Z&window_minutes=60"` → JSON has stages, sets, pickers.
3. Re-curl with `If-Modified-Since` → 304.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `snapshot.served` | `group_id`, `at`, `window_minutes`, `set_count`, `picker_count`, `members_total`, `request_id` (DEBUG) |
| `snapshot.served_304` | `group_id`, `request_id` (DEBUG) |

## 8. Out of scope

| Item | Where |
|---|---|
| Server-rendered image | The snapshot is JSON; FE uses `react-native-view-shot` to capture the rendered UI. |
| Multi-event snapshot | Group is 1:1 with event per ADR-006 § 4.25. |
| Snapshot history / archive | v2. |
| ETag (vs Last-Modified) | v2. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. FE-008 falls back to a "Snapshot temporarily unavailable" state. Existing snapshot screenshots people already shared remain valid (they're images, not live links).
