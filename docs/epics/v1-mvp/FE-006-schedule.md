# FE-006 — Schedule (All Stages grid + Timeline + Mine/Group filters + Day menu) (prototype `isSchedule`)

**Wave:** 3
**Type:** FE
**Blocked by:** FE-101, FE-005, BE-009, BE-013, BE-014, BE-015, BE-016
**Blocks:** —
**ADR references:** Prototype `isSchedule` block (lines 283–459); [calendar-spec](../../features/calendar-spec.md)

## 1. Problem statement

The festival's full lineup, presented two ways:

- **All Stages** — a wall-of-stages grid (vertical time × horizontal stage columns) where every set is a tappable card. Tapping cycles through "going / unpicked." (Drop the prototype's "maybe" lobe — cross-stack risk #1.)
- **Schedule timeline** — a single chronological list filtered by **Mine** or **Group**. Mine: my picks. Group: everyone's picks.

Plus a day menu (top-right caret) for picking Day 1/2/3/4 and a filter sheet for selecting which group members to include in the Group view.

This is the biggest FE ticket.

## 2. Actual solution

Stack-pushed screen with the day-selector + sub-tab toggle at top, then the active sub-view.

**Sub-tab toggle** (border-bottom underline): "All Stages" (grid icon) and "Schedule" (calendar icon).

**Day menu**: top-center "Day {N} ▼" tap → modal day list (1–N derived from event's `start_date..end_date`).

### 2.1 All Stages (`schedIsStages`)

Help text + legend ("Tap once for going") + search input that **dims** non-matching cards rather than hiding them.

Grid:

- Header row sticky at top — one tile per stage with stage-color dot + name.
- Vertical time axis: 1 hour = 84 px (`PXH=84`).
- Each set positions by `(starts_at - axisStart) * 84` from top.
- Width 138 px per stage column, 10 px between columns.
- Card shows artist name + start time. If "going", card fills with the stage color and the bottom-right has the user's avatar.

Tap → toggle going for that set. Snap-back if server LWW-loses.

### 2.2 Schedule timeline (`schedIsTimeline`)

Filter chips: "Group | ▼" (purple pill) + "★ Mine" (purple pill). Tap Group → filter sheet slides up to select members.

Three states:

- `filter == "none"`: empty-illustration state ("No Filter Selected").
- `filter == "mine"`: shows the user's own picks. If empty: "Pick your first set" empty state.
- `filter == "group"`: shows all members' picks (or filtered subset from the sheet). If empty: "No Group Sets Yet" empty state.

Each item: time (start + end stacked) + stage-color dot + connector line + card with artist name (Playfair Display 18px), stage label, and avatar row.

Mine view has an "UP NEXT" hero card at the top showing the next-upcoming pick (computed from current real-time clock). The "in 63min" countdown updates every minute.

### 2.3 Day menu

Modal centered card with day buttons 1..N. Selected day has purple bg.

### 2.4 Filter sheet

Bottom sheet with the group's member roster. Each row: avatar + name + checkbox. "Clear All" / "Done" header.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/src/screens/groups/Schedule.tsx` | Top-level orchestrator. |
| `apps/mobile/src/screens/groups/ScheduleHeader.tsx` | Day selector + sub-tabs. |
| `apps/mobile/src/screens/groups/AllStagesGrid.tsx` | Grid view. |
| `apps/mobile/src/screens/groups/StagesGridCard.tsx` | Single set card in the grid. |
| `apps/mobile/src/screens/groups/Timeline.tsx` | Timeline view (Mine + Group). |
| `apps/mobile/src/screens/groups/UpNextHero.tsx` | "Up Next" hero card. |
| `apps/mobile/src/screens/groups/TimelineRow.tsx` | Single row (mine or group). |
| `apps/mobile/src/screens/groups/DayMenu.tsx` | Day picker modal. |
| `apps/mobile/src/screens/groups/FilterSheet.tsx` | Member filter bottom sheet. |
| `apps/mobile/src/hooks/useScheduleData.ts` | Joins lineup + group state per day. |
| `apps/mobile/src/hooks/useUpNext.ts` | Computes the next-coming user pick, updating every 60 s. |
| `apps/mobile/src/utils/gridLayout.ts` | Grid math (column index, top px, height px). |
| `apps/mobile/src/utils/dayList.ts` | Derive day list from event `start_date`/`end_date`. |
| `apps/mobile/__tests__/screens/Schedule.test.tsx` | See § 7. |
| `apps/mobile/__tests__/screens/AllStagesGrid.test.tsx` | See § 7. |
| `apps/mobile/__tests__/screens/Timeline.test.tsx` | See § 7. |
| `apps/mobile/__tests__/hooks/useScheduleData.test.ts` | See § 7. |
| `apps/mobile/__tests__/hooks/useUpNext.test.ts` | See § 7. |
| `apps/mobile/__tests__/utils/gridLayout.test.ts` | See § 7. |
| `apps/mobile/__tests__/utils/dayList.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// useScheduleData.ts
export function useScheduleData(inviteCode: string): {
  isLoading: boolean;
  days: { label: string; isoDate: string }[];
  setsByDay: Map<string, SetWithPicksAndStage[]>;
};

// useUpNext.ts
export function useUpNext(mySets: SetWithStage[]): {
  nextSet: SetWithStage | null;
  inLabel: string;  // "in 63min", "in 2h 5min", "now"
};

// gridLayout.ts
export interface GridLayoutInput {
  axisStartHour: number;
  pxPerHour: number;
  stageOrder: string[];     // stage_ids
  columnWidth: number;
  columnGap: number;
  leftAxisWidth: number;
}

export interface GridSetPosition {
  left: number;
  top: number;
  height: number;
}

export function positionInGrid(
  set: { stage_id: string; starts_at: string; ends_at: string },
  input: GridLayoutInput,
): GridSetPosition;

// dayList.ts
export function deriveDayList(startDate: string, endDate: string, timezone: string): {
  label: string;       // "Day 1", "Day 2"
  isoDate: string;     // "2026-09-25"
  dayLabel: string;    // "FRIDAY" (from event_api_v1)
}[];
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Grid pixels per hour | 84 | Prototype line 661 `PXH=84`. |
| Stage column width | 148 px (header), 138 px (cards) | Prototype lines 318, 327. Card has 10px right margin → effective 148. |
| Stage column gap | 10 px | Prototype line 318. |
| Left axis gutter | 48 px | Prototype line 661. |
| Card min height | 46 px | Prototype line 674. |
| Card height computation | `max(duration_h * 84 - 8, 46)` | Prototype line 674. |
| Axis-start | `min(starts_at of any set on day) - 0.5h, floored` | Prototype line 661. |
| Axis-end | `max(ends_at of any set on day, 24.5)` | Prototype line 665. |
| Up Next refresh | 60 s (real-time) | Prototype `setTimeout` would be wrong on mount only; we use a real `setInterval`. |
| Toggle animation | 180 ms | Prototype `transition: .18s`. |
| Search dim opacity | 0.25 | Prototype line 327. |
| Filter sheet animation | 250 ms slide up from translateY=100% | Prototype `sheetUp`. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Event with 1 day | Day menu still present but with one option. |
| Empty event lineup | "No sets" empty state inside both sub-views. |
| User's only pick is currently in progress | UpNextHero shows it with "Now" label. |
| User has no picks (Mine) | "Pick your first set" illustration. |
| Group view, no member has picked anything | "No Group Sets Yet" empty state. |
| Set with `starts_at == ends_at` (zero-duration) | Card renders at 46-px min height. Defensive. |
| Set straddling midnight | Card spans across the day boundary in the grid; if `ends_at > 24h+startOfDay`, the card clips at the visible bottom and re-appears in the next day's grid? **No** — we render each day independently; the set appears in Day N (its `day_label`). User can see both halves by switching days. Document. |
| Sub-tab swap mid-pick mutation | Mutation continues; UI snaps to the new sub-tab. |
| User filter-sheet selects 0 members | "Showing 0 members" with empty-list result. |
| Group state polls in the middle of a pick toggle | Pending mutation continues; poll result merges via TanStack. |
| Long stage name | Single-line truncation in the column header. |
| Long artist name in a small card (46 px) | Single-line truncation. |
| Time axis label wraps | Use `numberOfLines={1}`. |
| `event.timezone` differs from device timezone | Render times in event-local timezone via `Intl.DateTimeFormat` with `timeZone: event.timezone`. |
| Pull-to-refresh | Calls TanStack `invalidateQueries` for both lineup and group state. |
| Search query empty | All cards full opacity. |
| Search query matches none | All cards dimmed. |
| Tap a dimmed card | Still toggles. |

## 7. Acceptable validation

**Tests:**

| File | Test name | Assertion |
|---|---|---|
| `dayList.test.ts` | `single_day_event_returns_one_entry` | start==end → 1 entry. |
| `dayList.test.ts` | `multi_day_returns_n_entries_in_order` | start..end inclusive returns N. |
| `dayList.test.ts` | `uses_event_timezone_for_date_math` | event tz Europe/Brussels → days don't shift by DST. |
| `gridLayout.test.ts` | `position_correct_for_known_set` | Set at 19:00 with axisStart=18 → top = 84 px. |
| `gridLayout.test.ts` | `column_index_matches_stage_order` | Stage 2 of 4 → left = 48 + 1*158 = 206 px. |
| `gridLayout.test.ts` | `height_floored_to_46` | Duration < 46/84 hours → height = 46. |
| `useScheduleData.test.ts` | `groups_sets_by_day_label` | Sets across 3 days → 3 buckets keyed by day_label. |
| `useScheduleData.test.ts` | `combines_lineup_and_picks` | Sets with `pickers` from group state. |
| `useUpNext.test.ts` | `returns_next_upcoming_set` | Mock clock = now; sets at now+30min and now+2h → returns the +30min. |
| `useUpNext.test.ts` | `inLabel_minutes_or_hours` | now+30min → "in 30min"; now+2h5min → "in 2h 5min"; now → "Now". |
| `useUpNext.test.ts` | `updates_every_minute` | Fast-forward 60s twice → 2 recomputes. |
| `useUpNext.test.ts` | `returns_null_when_no_future_picks` | All picks in past → null. |
| `AllStagesGrid.test.tsx` | `renders_one_card_per_set_for_active_day` | 5 sets on Day 1 → 5 cards. |
| `AllStagesGrid.test.tsx` | `tap_card_toggles_pick` | Tap unpicked → POST /picks; tap going → DELETE. |
| `AllStagesGrid.test.tsx` | `going_card_filled_with_stage_color` | Pick "going" → bg matches stage.color. |
| `AllStagesGrid.test.tsx` | `search_query_dims_non_matching` | query="effin" → matching card opacity 1, others 0.25. |
| `Timeline.test.tsx` | `filter_none_shows_empty_state` | filter="none" → "No Filter Selected" visible. |
| `Timeline.test.tsx` | `filter_mine_lists_user_picks_in_chronological_order` | 3 picks → 3 rows ascending. |
| `Timeline.test.tsx` | `filter_mine_empty_shows_pick_first_set_state` | No picks → illustration visible. |
| `Timeline.test.tsx` | `filter_group_shows_all_members_picks` | Group has 3 picks across 2 members → 3 rows; AvatarStack reflects each. |
| `Timeline.test.tsx` | `filter_sheet_toggles_member_inclusion` | Uncheck member A → A's picks hidden. |
| `Timeline.test.tsx` | `remove_button_in_mine_unpicks` | Tap ✕ on a mine row → DELETE /picks. |
| `Schedule.test.tsx` | `day_menu_switches_active_day` | Tap Day 3 → cards belong to Day 3. |
| `Schedule.test.tsx` | `sub_tab_swap_persists_filter` | Switch from Stages to Schedule and back → filter preserved. |
| `Schedule.test.tsx` | `back_chip_pops_to_group_detail` | Tap back → goBack. |

**Manual QA — DARK MODE ONLY:**

1. From Group Detail → "Schedule" → opens to Day 1, All Stages.
2. Scroll the grid — sticky stage headers stay.
3. Tap a card → fills with stage color + bottom-right avatar. Pop animation.
4. Tap again → reverts.
5. Search "ef" → other cards dim.
6. Switch sub-tab to Schedule → filter chips visible. Tap "Mine" — see picks list with "UP NEXT" hero updating every minute.
7. Tap "Group" → filter sheet slides up — toggle members → list updates.
8. Day menu (caret) → switch to Day 2 → cards refresh.
9. Have a second user (or test fixture) make a pick — within 15 s it shows up in Group view.
10. Visual parity with prototype lines 283–459.

**Structured-log lines:** N/A.

**Failure modes:**

- Lineup load fail → "Couldn't load lineup" + retry.
- Pick POST fail → toast + state snaps back.

## 8. Out of scope

| Item | Where |
|---|---|
| Offline pick queue | BACKLOG-019 (V1 ships network-only). |
| Conflict-overlap warning visualization | calendar-spec FE-CAL-006 — can land in this ticket or BACKLOG-022; default to BACKLOG-022 unless implementer has cycle. |
| Drag-to-schedule | Permanently out (calendar-spec). |
| Light theme | BACKLOG-001. |
| Tri-state "maybe" | Permanently out. |
| Synchronized scroll across members | Calendar-spec — out of v1. |
| Print / export | Out. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. "Schedule" button on GroupDetail → placeholder. Users can still see picks via per-day list on GroupDetail.
