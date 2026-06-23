# FE-004 — Join group (prototype `isJoin`)

**Wave:** 3
**Type:** FE
**Blocked by:** FE-101, BE-007
**Blocks:** —
**ADR references:** Prototype `isJoin` block (lines 124–146)

## 1. Problem statement

User has an invite code (from another member) and wants to join their group. Show a single-input screen, normalize the code on type, submit to BE-007, and route to the group detail on success.

## 2. Actual solution

`JoinGroup` screen — back chip + 64-px purple-ring icon + "Join a group" title + "Enter the invite code" subtitle + 8-char Space-Mono input + error message slot + tip "Tip: try K7M2X9PQ".

On every key press, uppercase the input + map I→1, L→1, O→0 (Crockford normalize) and clip to 8 chars. When length === 8, submit button becomes enabled.

Submit → POST `/api/groups/join` with `{invite_code}` → on 201/200 success, `navigation.replace('GroupDetail', { invite_code })`. On 404 → set `joinError=true` to render the red error.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/src/screens/groups/JoinGroup.tsx` | Screen. |
| `apps/mobile/src/hooks/useJoinGroup.ts` | Mutation. |
| `apps/mobile/src/utils/inviteCode.ts` | `normalizeCode(raw) -> string` — shared with possible deep-link path. |
| `apps/mobile/__tests__/screens/JoinGroup.test.tsx` | See § 7. |
| `apps/mobile/__tests__/utils/inviteCode.test.ts` | See § 7. |
| `apps/mobile/__tests__/hooks/useJoinGroup.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// inviteCode.ts
export function normalizeCode(raw: string): string;
// → uppercase, I→1, L→1, O→0, clip to 8

// useJoinGroup.ts
export function useJoinGroup(): UseMutationResult<
  GroupJoinResponse,
  ApiError,
  { invite_code: string; display_name_override?: string }
>;
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Input maxLength | 8 | ADR-006 § 4.22. |
| Submit-enabled threshold | length === 8 | Prototype line 595. |
| Submit-active style | `gradient.title` + `shadow.ctaActive` | Match Create button. |
| Error highlight | input border `#ff6a8a` | Prototype line 594. |
| Error message | "This invite link is invalid or expired" | Prototype line 138. |
| Letter-spacing | 0.18em | Prototype line 136. |
| Font family | Space Mono 700 18px | Prototype line 136. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| User types lowercase "k7m2x9pq" | Displayed as "K7M2X9PQ". |
| User types "I" | Displayed as "1". |
| User types "L" | Displayed as "1". |
| User types "O" | Displayed as "0". |
| User types "U" | Displayed verbatim (not in Crockford alphabet — submit will fail). Some Crockford specs map U→V; we don't, to match BE. |
| User pastes "k7m2x9pq" | Normalized + clipped to 8. |
| User pastes 16-char string | First 8 retained. |
| User pastes "1234" | Input shows "1234"; submit stays disabled. |
| Submit 200 (already a Member) | Navigate to GroupDetail with `is_new_member=false` — no toast. |
| Submit 201 (newly joined) | Navigate + small "Joined!" toast. |
| Submit 404 | Set `joinError=true`; input border red; error message visible; the submit button reverts to disabled style. |
| Submit network error | Toast "You're offline. Try again." |
| Already pressed submit + waiting | Second tap ignored (`isPending` disables). |
| Deep link `setlistpicker://join/K7M2X9PQ` | Open this screen with the code pre-filled and auto-submit. (Deep linking is BACKLOG-020; flag the hook here.) |

## 7. Acceptable validation

**Tests:**

| File | Test name | Assertion |
|---|---|---|
| `inviteCode.test.ts` | `normalize_uppercases` | normalizeCode("abcd") === "ABCD". |
| `inviteCode.test.ts` | `normalize_substitutes_i_l_o` | normalizeCode("ILO") === "110". |
| `inviteCode.test.ts` | `normalize_clips_to_8` | normalizeCode("ABCDEFGHIJ") === "ABCDEFGH". |
| `inviteCode.test.ts` | `normalize_keeps_u_verbatim` | normalizeCode("U") === "U". |
| `useJoinGroup.test.ts` | `posts_normalized_code` | mutate("k7m2x9pq") → fetch called with `K7M2X9PQ`. |
| `JoinGroup.test.tsx` | `submit_disabled_until_length_8` | Type 7 chars → disabled; 8 → enabled. |
| `JoinGroup.test.tsx` | `submit_404_shows_error` | Mock 404 → input border red; error text visible. |
| `JoinGroup.test.tsx` | `submit_success_navigates_to_group_detail` | Mock 201 → navigation.replace called. |
| `JoinGroup.test.tsx` | `paste_long_string_clips_to_8` | onChangeText("ABCDEFGHIJ") → state "ABCDEFGH". |
| `JoinGroup.test.tsx` | `back_chip_pops` | Tap back → goBack called. |
| `JoinGroup.test.tsx` | `tip_visible` | Tip text present. |

**Manual QA — DARK MODE ONLY:**

1. Home → "Join a group" → screen.
2. Type lowercase "k7m2x9pq" → uppercases.
3. Submit invalid code → red error.
4. Submit valid code → group detail.
5. Submit while already a member → group detail, no error.

**Structured-log lines:** N/A.

## 8. Out of scope

| Item | Where |
|---|---|
| Deep-link auto-join | BACKLOG-020. |
| QR-code join | v2. |
| Display-name-override step at join | Out — server defaults to user's display_name. |
| Light theme | BACKLOG-001. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. Home "Join a group" CTA breaks. Acceptable for short-term.
