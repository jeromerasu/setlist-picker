# FE-008 — Right-Now snapshot view + screenshot-share UX (new screen)

**Wave:** 3
**Type:** FE
**Blocked by:** FE-101, BE-017
**Blocks:** —
**ADR references:** [ADR-006 § 4.13, § 4.14](../../decisions/ADR-006-initial-data-schema.md); EPIC § 8 cross-stack risk #8

## 1. Problem statement

User wants to share "where will we be at time T" with the wider group chat / friends. The snapshot view is a self-contained, screenshotable layout of every stage at the chosen moment, with every member's plans denormalized so the screen capture stands alone. Tap the share icon to capture + open the native Share Sheet.

This screen is **not in the prototype** — see EPIC § 8 risk #8. Jerome may want a separate design review before opening it.

## 2. Actual solution

`RightNowSnapshot` screen pushed from GroupDetail (a third button next to "Invite friends" / "Schedule"? Or in a header overflow menu — implementer chooses; the FE-005 ticket allows either).

`route.params.invite_code` + optional `at` (defaults to now, in event-local timezone).

Header:

- Group name + event name (small).
- Time picker chip — "9:00 PM" → tap → date+time picker dial.
- "{N} of {M} friends going" hero count.
- Share icon (top-right).

Body — vertical stack of stage cards:

- Each stage card: stage-color dot + name on a row, then per-set blocks:
  - Set name + time range + AvatarStack of pickers' avatars.
  - "Empty stage" placeholder if no sets in window.

Empty stages — hide entirely (don't clutter the share).

Share button — `react-native-view-shot` captures the body view (excluding share button + nav). Resulting URI → `expo-sharing.shareAsync(uri, { mimeType: 'image/png' })`.

Polling: `useSnapshot(invite_code, at, window_minutes=60)` polls every 30s while screen foregrounded, conditional GET per BE-017.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/package.json` | Add `react-native-view-shot`, `@react-native-community/datetimepicker`. |
| `apps/mobile/src/screens/groups/RightNowSnapshot.tsx` | Screen. |
| `apps/mobile/src/screens/groups/SnapshotStageCard.tsx` | Per-stage card. |
| `apps/mobile/src/screens/groups/SnapshotSetRow.tsx` | Per-set row. |
| `apps/mobile/src/screens/groups/SnapshotTimePicker.tsx` | Time picker chip + sheet. |
| `apps/mobile/src/hooks/useSnapshot.ts` | Polling hook with If-Modified-Since. |
| `apps/mobile/src/utils/captureScreenshot.ts` | view-shot wrapper. |
| `apps/mobile/src/screens/groups/GroupDetail.tsx` | Add "Right Now" entry point. |
| `apps/mobile/__tests__/screens/RightNowSnapshot.test.tsx` | See § 7. |
| `apps/mobile/__tests__/hooks/useSnapshot.test.ts` | See § 7. |
| `apps/mobile/__tests__/utils/captureScreenshot.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// useSnapshot.ts
export function useSnapshot(
  inviteCode: string,
  at: Date,
  windowMinutes?: number,  // default 60
): UseQueryResult<GroupSnapshotResponse>;
// Polls every 30s while focused.

// captureScreenshot.ts
export async function captureAndShare(viewRef: React.RefObject<View>): Promise<void>;
// view-shot → shareAsync. Toast on success/fail.
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Default window | 60 min | Matches BE-017 default. |
| Poll interval | 30 s | ADR-006 § 4.14. |
| Capture format | PNG | Lossless; shareable to chat apps. |
| Capture resolution | Native pixel ratio (e.g. 3x on iOS) | Crisp on Retina. |
| Default `at` | now (in event tz if event hasn't started; current real-time if event in progress) | Sensible. |
| Time picker step | 5 minutes | Matches typical festival schedule granularity. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| `at` outside event window (before start or after end) | Render with empty stages → "No sets at this time" footer. Time picker can still scroll out. |
| Group has 0 members other than caller | "1 of 1 friend going" — singular "friend." |
| No member picked anything in the window | All stages render empty (if all stages have sets but no pickers) → "No picks in this window." |
| Single set in window | Single card. |
| Time picker switches `at` | Re-fetch with new `at`. |
| Tap share while snapshot is loading | Button disabled until first data. |
| view-shot fails (rare) | Toast "Couldn't capture screenshot." |
| expo-sharing not available (very old device) | Save to camera roll as fallback via `expo-media-library`. (BACKLOG-023 if outside scope; v1 ships expo-sharing only.) |
| Group archived (`archived_at != null`) | Show archived badge; sharing still works. |
| `event.timezone` Europe/Brussels but device in PST | Time labels render in event tz. |
| User switches to dark/light theme mid-capture | Capture reflects current theme (dark always in v1). |
| Capture happening simultaneously with a polled refresh | Use the snapshot at the moment the share button was tapped; freeze the render briefly with `requestAnimationFrame`. |

## 7. Acceptable validation

**Tests:**

| File | Test name | Assertion |
|---|---|---|
| `useSnapshot.test.ts` | `polls_every_30s` | Fast-forward 60 s → 2 fetches. |
| `useSnapshot.test.ts` | `sends_if_modified_since` | Second call has header. |
| `useSnapshot.test.ts` | `default_window_60` | Query string `?window_minutes=60`. |
| `captureScreenshot.test.ts` | `view_shot_then_share_called` | Mock capture → URI; share called with URI. |
| `captureScreenshot.test.ts` | `view_shot_failure_shows_toast` | Mock reject → toast visible. |
| `RightNowSnapshot.test.tsx` | `renders_stages_with_sets` | Mock snapshot → cards render. |
| `RightNowSnapshot.test.tsx` | `hides_empty_stages` | Stage with empty sets → hidden. |
| `RightNowSnapshot.test.tsx` | `renders_pickers_avatar_stack` | Set with 2 pickers → AvatarStack with 2 avatars. |
| `RightNowSnapshot.test.tsx` | `share_button_disabled_while_loading` | isLoading → button disabled. |
| `RightNowSnapshot.test.tsx` | `time_picker_changes_at_param` | Pick new time → useSnapshot called with new `at`. |
| `RightNowSnapshot.test.tsx` | `singular_friend_label_when_one` | members_total=1 → "1 friend." |
| `RightNowSnapshot.test.tsx` | `displays_event_timezone_times` | event.timezone = Europe/Brussels → set times in CEST. |

**Manual QA — DARK MODE ONLY:**

1. From GroupDetail → "Right Now" → screen.
2. Default to now; see stages with picks.
3. Pick a new time → screen updates.
4. Tap share → camera/file picker UI; share to Messages → confirm the screenshot is legible and self-contained (event name visible, group name visible, member names visible).
5. Repeat with a group of 3 — confirm member rendering.
6. Switch `at` to 4 AM → empty state.

**Structured-log lines:** N/A.

## 8. Out of scope

| Item | Where |
|---|---|
| Server-rendered image | Permanently out — client capture is sufficient. |
| Multi-time snapshot (compare two `at` values) | v2. |
| Embed group invite code in the screenshot | Could be additive — defer to BACKLOG-024 if Jerome wants. |
| Saving snapshots to a personal "gallery" inside the app | v2. |
| Light theme | BACKLOG-001. |
| Push notifications when "everyone is at the same stage" | v1.x. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. Right-Now entry point on GroupDetail removed. No data loss.
