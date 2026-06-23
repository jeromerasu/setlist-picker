# FE-005 — Group detail + Artists tabs + invite share (prototype `isGroup`)

**Wave:** 3
**Type:** FE
**Blocked by:** FE-101, BE-009, BE-013
**Blocks:** FE-006, FE-007
**ADR references:** Prototype `isGroup` block (lines 149–234), [ADR-006 § 4.12](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

Tap a group on Home → arrive on the group's home screen. Show group identity + invite code + share + jump-to-schedule, then the artists list with two presentation modes (All Artists alphabetical / Per-day grouped by stage).

## 2. Actual solution

`GroupDetail` screen, `route.params.invite_code`. Polls `GET /api/groups/{invite_code}` every 15 s (TanStack Query `refetchInterval`). Reads `GET /api/events/{event_id}/lineup` once (cached).

**Top half (`paddingBottom 1px border`):**

- Gradient title (group name).
- 4 meta rows with emoji icons: 🎪 event, 📅 dates, 📍 location, 🔑 invite code in Space Mono.
- 2 buttons: "Invite friends" (outline + share icon) and "Schedule" (gradient + calendar icon).
- "✓ Invite copied — \"Join my group on Setlist! Group code: {code}\"" toast on copy (auto-hides 2.6 s).

Invite share: tap "Invite friends" → call `expo-sharing.shareAsync` with the share text (cross-platform Share Sheet). Fallback to `Clipboard.setStringAsync` + the prototype's toast.

**Bottom half (Artists):**

- Section header: "Artists" + "{count} acts" right-aligned.
- Horizontal pill tabs: "All Artists / Day 1 / Day 2 / Day 3 / Day 4". Day-N tabs are derived from `set.day_label` per cross-stack risk #4. Only show day tabs that actually have sets.

**All Artists view** (sorted alphabetically):
List of set rows: 46×46 gradient tile + artist name + genre · genre + stage-color dot. Tap → artist modal (FE-007).

**Per-day view** (grouped by stage chronologically):
For each stage with at least one set on this day:
  - Stage label (Orbitron 12px uppercase with stage color + glow).
  - Set rows: artist name + time range. AvatarStack of group members going. Picked-state icon: pink-cyan gradient circle with check OR empty outline circle.
  - Tap a set toggles "going" state — calls `POST /picks` (BE-015). Tap again (or DELETE) to unpick.

**Important:** the per-day list uses the binary `going / not picked` state (no maybe). Cross-stack risk #1 — drop the prototype's tri-state.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/src/screens/groups/GroupDetail.tsx` | Screen orchestrator. |
| `apps/mobile/src/screens/groups/GroupDetailHeader.tsx` | Top half. |
| `apps/mobile/src/screens/groups/GroupDetailArtists.tsx` | Bottom half. |
| `apps/mobile/src/screens/groups/ArtistRowAll.tsx` | All-artists row. |
| `apps/mobile/src/screens/groups/ArtistRowDay.tsx` | Per-day row with picker state. |
| `apps/mobile/src/hooks/useGroupState.ts` | TanStack polling + `If-Modified-Since`. |
| `apps/mobile/src/hooks/useEventLineup.ts` | Read-once lineup hook. |
| `apps/mobile/src/hooks/usePickToggle.ts` | LWW-aware pick mutation. |
| `apps/mobile/src/utils/inviteShare.ts` | Cross-platform share text + Share Sheet. |
| `apps/mobile/src/utils/dayBuckets.ts` | Group sets by `day_label`. |
| `apps/mobile/__tests__/screens/GroupDetail.test.tsx` | See § 7. |
| `apps/mobile/__tests__/hooks/useGroupState.test.ts` | See § 7. |
| `apps/mobile/__tests__/hooks/usePickToggle.test.ts` | See § 7. |
| `apps/mobile/__tests__/utils/inviteShare.test.ts` | See § 7. |
| `apps/mobile/__tests__/utils/dayBuckets.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// useGroupState.ts
export function useGroupState(inviteCode: string): UseQueryResult<GroupStateResponse>;
// Polls every 15s; sends If-Modified-Since.

// useEventLineup.ts
export function useEventLineup(eventId: string): UseQueryResult<EventLineupResponse>;
// staleTime: Infinity; one fetch per app session.

// usePickToggle.ts
export function usePickToggle(inviteCode: string): {
  toggle: (setId: string, currentlyGoing: boolean) => Promise<void>;
  isPending: (setId: string) => boolean;
};
// Writes state_clock_ms = Date.now(); POST /picks for going, DELETE /picks/{set_id} for unpick.

// inviteShare.ts
export async function shareInvite(code: string): Promise<{ method: "share-sheet" | "clipboard" }>;
// expo-sharing first; on unavailable platforms, Clipboard + return "clipboard".

// dayBuckets.ts
export function bucketByDay(sets: SetDetail[]): { day_label: string; sets: SetDetail[] }[];
// Sorted by day_label following the event's start_date order.
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Poll interval | 15_000 ms | ADR-006 § 4.14. |
| Lineup staleTime | Infinity (within session) | Lineup doesn't change during a single session. |
| Invite toast duration | 2600 ms | Prototype line 605. |
| Stage glow radius | `0 0 8px {color}` | Prototype line 204. |
| Picked-state pop animation | 250 ms | DESIGN-TOKENS `motion.pickCheckPop`. |
| Tab active bg | `neon.purple` | Prototype line 610. |
| Per-day stage label font | Orbitron 700 12px, letter-spacing 0.08em | Prototype line 204. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Polled state has more members than lineup expects | Render all members; no problem. |
| Lineup load fails | Show "Couldn't load lineup" empty state in the artists section; top half still works. |
| User taps a set's "going" toggle | Optimistic update; if server LWW-loses, snap back to server state on next poll. |
| User toggles rapidly (going → not → going) | Last write wins; queue via LWW; no jitter. |
| Day tab has no sets for that day | Tab hidden. |
| Event has only 1 day | Show only "All Artists" tab — day-tab row is hidden. |
| Group has 0 picks | "0 acts going" in section header? No — `{artistCount} acts` shows the total acts on the day (prototype line 177). Don't conflate. |
| Member has no display_name override and no display_name → username | AvatarStack shows username initials. |
| Member's `avatar_color` collides with another member's | OQ-07 — accepted; both look the same. Document on hover/long-press: name fallback (BACKLOG-003 if user reports). |
| Invite share unavailable (e.g. simulator with no share targets) | Fall back to clipboard + toast. |
| Network offline | Show cached state from TanStack cache; offline badge top-right; pick toggles queue to expo-sqlite (BACKLOG-019 if not done — for v1, fail fast with a "you're offline" toast). |
| User picks a set then immediately leaves the group | FE-009 confirmation dialog catches before destructive POST; if user confirms, picks cascade-delete server-side. |

## 7. Acceptable validation

**Tests:**

| File | Test name | Assertion |
|---|---|---|
| `useGroupState.test.ts` | `polls_every_15s` | Mock fetch → fast-forward 30 s → 2 calls. |
| `useGroupState.test.ts` | `sends_if_modified_since_after_first_response` | First call no header; second call has `If-Modified-Since`. |
| `useGroupState.test.ts` | `304_uses_cached_data` | Mock 304 → response unchanged. |
| `usePickToggle.test.ts` | `toggle_going_posts_with_state_clock` | Tap "going" → POST `/picks` body has `state="active"`, `state_clock_ms` ≈ now. |
| `usePickToggle.test.ts` | `toggle_unpick_calls_delete` | Tap going set → DELETE `/picks/{set_id}` with `state_clock_ms`. |
| `usePickToggle.test.ts` | `lww_loss_snaps_back_on_next_poll` | Server returns LWW-lost → next poll's data is the truth; UI re-renders. |
| `inviteShare.test.ts` | `share_sheet_available_uses_sharing` | Mock expo-sharing available → shareAsync called. |
| `inviteShare.test.ts` | `falls_back_to_clipboard` | shareAsync rejects → Clipboard.setStringAsync called. |
| `dayBuckets.test.ts` | `groups_by_day_label_preserves_order` | Sets with day_label FRIDAY, SATURDAY, SUNDAY → bucketed in event-date order. |
| `dayBuckets.test.ts` | `unknown_day_label_at_end` | Set with unrecognized day_label → bucket appears last. |
| `GroupDetail.test.tsx` | `renders_invite_code_with_monospace` | Code text uses Space Mono font. |
| `GroupDetail.test.tsx` | `invite_button_calls_share_invite` | Tap → shareInvite called. |
| `GroupDetail.test.tsx` | `schedule_button_navigates_to_schedule` | Tap → navigation.navigate('Schedule') called. |
| `GroupDetail.test.tsx` | `tabs_only_show_days_with_sets` | Event has Day 1 and Day 3 → tabs "All / Day 1 / Day 3". |
| `GroupDetail.test.tsx` | `tap_artist_row_navigates_to_artist_modal` | Tap → navigation.navigate('Artist', { artist_name }). |
| `GroupDetail.test.tsx` | `tap_picked_set_unpicks` | Pre-seed pick "going" → tap → DELETE issued. |
| `GroupDetail.test.tsx` | `tap_unpicked_set_picks` | Empty state → tap → POST issued. |

**Manual QA — DARK MODE ONLY:**

1. Open a group → see header with name (gradient), event, date, location, code.
2. Tap "Invite friends" → Share Sheet OR toast.
3. Tap "Schedule" → FE-006 opens.
4. Tap "All Artists" → alphabetical list; tap any artist → FE-007 opens.
5. Tap "Day 1" → stage-grouped; tap a set → check icon appears (pop animation).
6. Tap again → empty circle.
7. Visual parity with prototype lines 149–234.
8. Wait 15 s — second member's pick (made on a second device) appears.

**Structured-log lines:** N/A.

## 8. Out of scope

| Item | Where |
|---|---|
| `state="maybe"` tri-state from the prototype | Permanently out per cross-stack risk #1. |
| Group rename UI | BACKLOG-009 / FE-009. |
| Member roster slide-over | Not in v1 surface — implicit via AvatarStack only. v2. |
| Conflict warning on overlap | Calendar-spec FE-CAL-006 — surfaced in FE-006, not here. |
| Light theme | BACKLOG-001. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. GroupDetail goes to placeholder; FE-001 → tapping a card shows "Coming soon."
