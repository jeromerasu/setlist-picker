# FE-009 — Account / profile (You tab) + leave-group confirmation

**Wave:** 3
**Type:** FE
**Blocked by:** FE-101, BE-003, (BE-021 leave-group endpoint if it lands)
**Blocks:** —
**ADR references:** [ADR-006 § 4.21, § 4.28](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

The bottom-nav "You" tab is currently a placeholder. We need:

- Display the current user (display name, username, email, avatar color, sign-in method).
- Let the user change display name + avatar color.
- Logout.
- For each of the user's groups, allow Leave (with confirmation dialog).

The screen is not in the prototype — see EPIC § 5 wave 3 note. Jerome may want a separate visual pass.

## 2. Actual solution

`AccountProfile` screen — the You tab's root.

Sections:

- **Identity** (top): big Avatar (48 px) showing current `avatar_color` + initials. Below: display name (Manrope 800 24px). Below that: `@username` (if local) or "Signed in with Apple/Google" (if SSO).
- **Edit profile** card:
  - Display name input.
  - Avatar color swatches (12 from the palette in BE-003 § 5).
  - "Save" CTA (only enabled if changed).
- **Your groups** card:
  - For each group: row with name + "Leave" button.
  - Leave tap → modal confirmation: "Leave \"<group name>\"? Your picks will be deleted." Buttons: "Cancel" / "Leave group" (destructive red).
- **Account** card:
  - Sign-in method badge (Apple / Google / Local).
  - Email (if present).
- **Sign out** button (outline) at the bottom.

ADR-006 § 4.28 forward-compat criterion is met by the modal copy.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/src/screens/account/AccountProfile.tsx` | Screen. |
| `apps/mobile/src/screens/account/AvatarColorPicker.tsx` | 12-swatch picker. |
| `apps/mobile/src/screens/account/LeaveGroupModal.tsx` | Confirmation modal. |
| `apps/mobile/src/hooks/useUpdateProfile.ts` | PATCH /users/me mutation. |
| `apps/mobile/src/hooks/useLeaveGroup.ts` | POST /groups/{code}/leave mutation. (Endpoint is BE-021 — flag if not yet built.) |
| `apps/mobile/src/auth/AuthContext.tsx` | Already exposes `signOut`; this ticket may add `me` cache. |
| `apps/mobile/__tests__/screens/AccountProfile.test.tsx` | See § 7. |
| `apps/mobile/__tests__/screens/LeaveGroupModal.test.tsx` | See § 7. |
| `apps/mobile/__tests__/hooks/useUpdateProfile.test.ts` | See § 7. |
| `apps/mobile/__tests__/hooks/useLeaveGroup.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// useUpdateProfile.ts
export function useUpdateProfile(): UseMutationResult<
  UserOut,
  ApiError,
  { display_name?: string; email?: string; avatar_color?: string }
>;

// useLeaveGroup.ts
export function useLeaveGroup(): UseMutationResult<
  GroupLeaveResponse,
  ApiError,
  { invite_code: string }
>;
```

`GroupLeaveResponse` already in `docs/schemas/reference/v1_pydantic.py`.

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Avatar swatch grid | 4 cols × 3 rows = 12 | Matches palette. |
| Display name max length | 80 (matches BE) | Don't surprise the user. |
| Leave confirmation copy | "Leave \"<group name>\"? Your picks will be deleted." | ADR-006 § 4.28 forward-compat. |
| Leave button color | `text.error` (`#ff6a8a`) | Destructive signaling. |
| Sign-out style | OutlineButton (not gradient) | Less alarming than destructive. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| User is SSO (Apple/Google) with NULL username | Show "Signed in with Apple" / "Signed in with Google" badge; hide @username row. |
| User changes display name to empty | Save disabled (min_length=1). |
| User changes display name then leaves form without saving | Discard changes on unmount (no auto-save). |
| User changes avatar color → save → cancel before tap | Local state reverts. |
| BE returns `email_taken` on PATCH | Inline error under email field. |
| BE returns `username_taken` (no — we don't edit username) | N/A. |
| Save while offline | Mutation throws; toast. |
| Leave-group modal: tap outside | Modal closes; no destructive call. |
| Leave-group success | Invalidate `useMyGroups`; modal closes; toast "Left \"<group name>\"". |
| Leave-group fails (network) | Modal stays open; toast. |
| User signs out | `clearTokens()` → RootNavigator switches to AuthStack. |
| User has 0 groups | "Your groups" card hidden. |
| User has > 20 groups | Scrolls naturally. |
| Avatar-color collision with another member in a group | OQ-07 — accepted. No special UI. |

## 7. Acceptable validation

**Tests:**

| File | Test name | Assertion |
|---|---|---|
| `useUpdateProfile.test.ts` | `patches_only_changed_fields` | display_name changed, color unchanged → PATCH body has only display_name. |
| `useUpdateProfile.test.ts` | `success_invalidates_me_query` | Mock success → queryClient.invalidateQueries(['me']) called. |
| `useLeaveGroup.test.ts` | `posts_to_leave_endpoint` | mutate({invite_code:'X'}) → POST `/api/groups/X/leave`. |
| `useLeaveGroup.test.ts` | `success_invalidates_my_groups` | After success → invalidate. |
| `LeaveGroupModal.test.tsx` | `displays_group_name_in_copy` | Modal text contains group name. |
| `LeaveGroupModal.test.tsx` | `cancel_does_not_invoke_leave` | Tap Cancel → useLeaveGroup not called. |
| `LeaveGroupModal.test.tsx` | `confirm_invokes_leave` | Tap "Leave group" → useLeaveGroup.mutate called. |
| `LeaveGroupModal.test.tsx` | `outside_tap_closes_modal` | Tap backdrop → onClose called. |
| `AccountProfile.test.tsx` | `renders_user_identity` | display name + @username visible. |
| `AccountProfile.test.tsx` | `hides_username_for_sso` | auth_provider='apple' + username=null → no @username row. |
| `AccountProfile.test.tsx` | `save_disabled_when_no_changes` | Initial render → Save disabled. |
| `AccountProfile.test.tsx` | `save_enabled_after_color_change` | Pick new swatch → Save enabled. |
| `AccountProfile.test.tsx` | `sign_out_clears_tokens` | Tap → clearTokens called. |
| `AccountProfile.test.tsx` | `leave_button_opens_modal` | Tap → modal appears. |

**Manual QA — DARK MODE ONLY:**

1. Bottom-nav "You" → screen.
2. Change display name + tap Save → name updates instantly; toast.
3. Pick new avatar color → Save → Home avatar reflects.
4. Tap "Leave" on a group → modal copy includes group name → tap "Leave group" → group disappears from Home.
5. Sign out → returns to AuthLanding.
6. Re-login → see persisted display name + color.

**Structured-log lines:** N/A.

## 8. Out of scope

| Item | Where |
|---|---|
| Change password (local users) | BACKLOG-004. |
| Delete account | BACKLOG-025. |
| Linked devices view | Out — BE-020 has data but no UI in v1. |
| Privacy / data export | Out. |
| Light theme toggle | OQ-04 → BACKLOG-001. |
| Notification preferences | v1.x push pipeline. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. "You" tab returns to placeholder. Sign-out still works via a hidden dev gesture (optional) or by clearing app data. Coordinate with BE-021 if leave-group endpoint is mid-flight.
