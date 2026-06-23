# FE-002 — New-group form (prototype `isCreate`)

**Wave:** 3
**Type:** FE
**Blocked by:** FE-101, FE-102, FE-001, FE-003, BE-006
**Blocks:** —
**ADR references:** Prototype `isCreate` block (lines 69–94); [ADR-006 § 4.25](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

User taps "+ CREATE A GROUP" on Home and lands on a two-field form: group name (text input) + event (button that opens FE-003 event picker). Submit becomes enabled (gradient + shadow) only when both filled.

## 2. Actual solution

`CreateGroup` screen with:

- Back chip (top-left) → pop.
- "New group" title.
- Section label "Group name" + input.
- Section label "Event" + button (label = selected event name, or "Choose a festival" placeholder).
- Submit button at bottom, disabled state OR active gradient based on `(name.trim() && event)`.

Event selection: navigate to `EventPicker` (FE-003) and return with the event id + name via React Navigation's `route.params.selectedEvent`.

Submit handler: `useCreateGroup` mutation → POST `/api/groups` → on success, invalidate `useMyGroups`, replace navigation to `GroupDetail(invite_code)` so back doesn't return to the form. On error, toast with the BE error_code.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/src/screens/groups/CreateGroup.tsx` | Main screen. |
| `apps/mobile/src/hooks/useCreateGroup.ts` | Mutation hook. |
| `apps/mobile/__tests__/screens/CreateGroup.test.tsx` | See § 7. |
| `apps/mobile/__tests__/hooks/useCreateGroup.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// useCreateGroup.ts
export function useCreateGroup(): UseMutationResult<
  GroupCreateResponse,
  ApiError,
  { name?: string; event_id: string }
>;
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Group name max length | 80 chars (matches BE) | Prevent surprises. |
| Group name placeholder | "e.g. ravefam" | Prototype line 79. |
| Event button placeholder | "Choose a festival" | Prototype line 84. |
| Submit-disabled style | transparent bg, `border.disabled`, `text.placeholder` | Prototype lines 91. |
| Submit-active style | `gradient.title` bg, `shadow.ctaActive` | Prototype line 91. |
| Submit transition | 200 ms | Prototype `transition: .2s`. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Name input only whitespace | Submit stays disabled (name.trim() empty). |
| Long name (80+ chars) | `maxLength={80}` clips. |
| Event button tapped twice quickly | Single navigation to FE-003. |
| User picks event → backs out without confirming → returns to form | Event retained. |
| User picks event A → re-taps event button → returns with event B | Form shows event B. |
| Submit while offline | Mutation throws network error → toast. Don't clear form. |
| BE 404 `event_not_found` (the picked event got deleted in the gap) | Toast "That festival is no longer available." Clear event selection. |
| BE 422 (validation) | Should never happen — FE filters; if it does, generic error toast. |
| Successful create | `useMyGroups` invalidates; FE-001 reloads next time we visit it. |

## 7. Acceptable validation

**Tests:**

| Test name | Assertion |
|---|---|
| `renders_name_input_and_event_button` | Both visible. |
| `submit_disabled_initially` | No name, no event → submit greyed. |
| `submit_enabled_when_name_and_event_present` | Fill both → gradient style. |
| `submit_disabled_when_name_only_whitespace` | name="   " + event → disabled. |
| `event_button_tap_navigates_to_event_picker` | Tap → navigate called with `EventPicker`. |
| `route_param_selectedEvent_fills_event_label` | navigate('Create', { selectedEvent: {...} }) → label shows event name. |
| `submit_invokes_useCreateGroup` | Tap submit → mutate called with name + event_id. |
| `success_navigates_to_group_detail` | Mock response → `navigation.replace('GroupDetail', { invite_code: 'X' })` called. |
| `success_invalidates_my_groups_query` | After success → queryClient.invalidateQueries called. |
| `error_event_not_found_clears_event` | Mock 404 → event state cleared; toast visible. |

**Manual QA — DARK MODE ONLY:**

1. Home → "+ CREATE A GROUP" → form.
2. Type name → submit stays disabled until event picked.
3. Tap "Choose a festival" → FE-003 → select EDC → return.
4. Submit becomes enabled, gradient + shadow.
5. Tap submit → spinner → group detail screen for new group.
6. Visual parity with prototype lines 69–94.

**Structured-log lines:** N/A.

## 8. Out of scope

| Item | Where |
|---|---|
| Inline new-festival entry | OQ-03 — curated only. |
| Avatar / theme override per group | Out — uses HUES rotation. |
| Light theme | BACKLOG-001. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. Create CTA on Home becomes a no-op or shows a "Coming soon" placeholder.
