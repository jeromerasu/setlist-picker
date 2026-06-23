# FE-003 — Event picker (prototype `isEventPicker`)

**Wave:** 3
**Type:** FE
**Blocked by:** FE-101, BE-012
**Blocks:** FE-002
**ADR references:** Prototype `isEventPicker` block (lines 97–121)

## 1. Problem statement

User from FE-002 needs to pick a festival. Show the list of available events with text search.

## 2. Actual solution

`EventPicker` screen — back chip + "Choose event" title + search input + scrollable list.

Each row: 46×46 colored mono-letter tile + name (bold 15px) + meta line ("date · location"). Tap → returns to FE-002 with the selected event via `navigation.navigate('CreateGroup', { selectedEvent: {...} })`.

Search input is debounced (300 ms) and queries `GET /api/events?q=`. Empty `q` → all events. Empty result → "No festivals match \"q\"" message.

The mono-letter tile background is computed from the event name (first 2 chars uppercased + a hash-stable HUES gradient).

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/src/screens/groups/EventPicker.tsx` | Screen. |
| `apps/mobile/src/hooks/useEvents.ts` | Debounced search hook. |
| `apps/mobile/src/utils/eventTile.ts` | Mono letter + gradient derivation. |
| `apps/mobile/__tests__/screens/EventPicker.test.tsx` | See § 7. |
| `apps/mobile/__tests__/hooks/useEvents.test.ts` | See § 7. |
| `apps/mobile/__tests__/utils/eventTile.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// useEvents.ts
export function useEvents(query: string): UseQueryResult<EventListResponse>;

// eventTile.ts
export function deriveMono(name: string): string;          // first 2 alphanums upper
export function deriveTileGradient(name: string): string;  // HUES[hash(name) % 6]
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Search debounce | 300 ms | Tap-throughput vs noise. |
| `q` min for trigger | 0 (empty triggers the all-events query) | Matches prototype. |
| Tile size | 46 × 46 | Prototype line 112. |
| Row gap | 9 px | Prototype line 109. |
| Stale time | 60 s | Event list rarely changes; reduce request volume. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Empty query | All events returned, sorted by start_date ASC. |
| `q="zzz"` (no match) | "No festivals match \"zzz\"" message visible. |
| Network offline | Show cached list with offline badge. |
| User types fast and submits before debounce fires | Search input commits immediately when length stabilizes. |
| Tap event → debounce hasn't fired yet | Tap still works — debounce only gates the search; selection is sync. |
| Event with no `location` | Display "date" only (no "· location"). |
| Event name length > 20 chars | 1-line truncation. |
| Mono letter for "3M³" (special chars) | Skip non-alphanums; if no alphanums, fall back to "??" tile. |

## 7. Acceptable validation

**Tests:**

| File | Test name | Assertion |
|---|---|---|
| `useEvents.test.ts` | `query_param_passed_to_be` | `useEvents("edc")` → URL has `?q=edc`. |
| `useEvents.test.ts` | `debounces_on_typing` | Type fast → only one BE call after 300 ms. |
| `eventTile.test.ts` | `derive_mono_from_simple_name` | "EDC Las Vegas" → "ED". |
| `eventTile.test.ts` | `derive_mono_skips_special_chars` | "!!Foo" → "FO". |
| `eventTile.test.ts` | `derive_mono_falls_back_to_question_marks` | "🎵🎶" → "??". |
| `eventTile.test.ts` | `derive_tile_gradient_stable_for_name` | Same name → same gradient string across calls. |
| `EventPicker.test.tsx` | `renders_all_events_initially` | 7 events → 7 rows. |
| `EventPicker.test.tsx` | `filters_on_search` | Type "edc" → only matching rows after debounce. |
| `EventPicker.test.tsx` | `empty_result_shows_no_match_message` | Type "zzz" → empty-state text visible. |
| `EventPicker.test.tsx` | `tap_event_navigates_back_with_payload` | Tap → `navigation.navigate('CreateGroup', { selectedEvent: e })`. |
| `EventPicker.test.tsx` | `back_chip_pops_without_selection` | Tap back → goBack called; no payload. |

**Manual QA — DARK MODE ONLY:**

1. From FE-002, tap "Choose a festival" → list visible.
2. Type "edc" → 1 result.
3. Clear → all results.
4. Tap "EDC Las Vegas 2026" → returns to FE-002 with event selected.
5. Visual parity with prototype lines 97–121.

**Structured-log lines:** N/A.

## 8. Out of scope

| Item | Where |
|---|---|
| User-submitted events | OQ-03 / v2. |
| Featured / pinned ordering beyond seed | OQ-03. |
| Filter by date / location chip | v2. |
| Light theme | BACKLOG-001. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. FE-002's event button errors when tapped. Coordinate.
