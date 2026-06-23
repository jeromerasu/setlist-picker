# FE-001 — Groups list (Home screen, prototype `isGroups`)

**Wave:** 3
**Type:** FE
**Blocked by:** FE-101, FE-102, BE-008
**Blocks:** —
**ADR references:** Prototype `isGroups` block (lines 36–66)

## 1. Problem statement

Authenticated user lands on the Home tab. Show every group they're a Member of as a tappable card. Two CTAs at the bottom: "+ CREATE A GROUP" and "Join a group". Empty state when no groups.

## 2. Actual solution

Reads `GET /api/users/me/groups` (BE-008) via TanStack Query. Renders a vertical scroll of `GroupCard` components. Each card:

- 96-px tall hero area with a radial gradient (rotated through `HUES[]` based on group position).
- Bottom-fade scrim over the hero.
- Group name overlay on the hero.
- Below: emoji icon + event name; emoji icon + dates; emoji icon + member count.

Cards tap → `groupDetail` screen (FE-005), pushing onto the Home stack.

Bottom CTAs:

- Pink-violet-cyan gradient "+ CREATE A GROUP" → push `create` (FE-002).
- Outline "Join a group" → push `join` (FE-004).

Empty state (no groups): cosmic empty illustration + headline "No groups yet" + body "Create a group to start planning, or join one with an invite code." The same two CTAs slide up into the body area.

Pull-to-refresh re-invalidates the query.

The bottom-nav `GlassBottomNav` stays mounted (it's on the BottomTabs layer above the stack).

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/src/screens/groups/GroupsList.tsx` | Main screen. |
| `apps/mobile/src/screens/groups/GroupCard.tsx` | Card component. |
| `apps/mobile/src/hooks/useMyGroups.ts` | TanStack Query hook. |
| `apps/mobile/src/theme/heroes.ts` | The `HUES[]` array as TS constants. |
| `apps/mobile/__tests__/screens/GroupsList.test.tsx` | See § 7. |
| `apps/mobile/__tests__/components/GroupCard.test.tsx` | See § 7. |
| `apps/mobile/__tests__/hooks/useMyGroups.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// useMyGroups.ts
export function useMyGroups(): UseQueryResult<MyGroupListResponse>;

// GroupCard.tsx
interface GroupCardProps {
  group: MyGroupListItem;
  heroGradient: string;   // from HUES[]
  onPress: () => void;
}
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Card height (hero) | 96 px | Prototype line 48. |
| Card padding bottom | 13–15 px | Prototype lines 52–55. |
| HUES rotation modulo | 6 | DESIGN-TOKENS § 1.7. |
| Pull-to-refresh tint | `neon.purple` | Brand-consistent. |
| Bottom CTA placement | absolute, `bottom: 90` (above bottom nav) | Prototype line 61. |
| Scroll area max height (above CTAs) | `screen - 90 (CTAs) - 64 (nav) - 20 (insets)` | Avoids overlap with CTAs. |
| Stale time | 15 s | Matches the 15s poll standard. |
| Query refetch on focus | yes | User just navigated to the tab; show fresh data. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| User in 0 groups | Empty state with both CTAs visible inline. |
| User in 1 group | Single card, CTAs at the absolute bottom. |
| User in > 6 groups | HUES rotates (`groups[6]` uses `HUES[0]` again). |
| Group has `archived_at != null` | Card gets a small "ARCHIVED" pill in the upper-right of the hero. |
| Loading | Skeleton card (`GlassCard` with shimmer animation). 2-card placeholder. |
| Error | Empty state with "Couldn't load groups" + retry button. |
| Network offline | Show stale data from TanStack cache + offline badge in the top-right of the screen. |
| Group event name is very long (> 40 chars) | Single-line truncation with ellipsis. |
| Group's member count = 1 (just creator) | "1 member" (singular). |
| Tap "+ CREATE A GROUP" but the user has no token (race) | `fetchWithAuth` throws → `RootNavigator` switches to AuthStack. |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `useMyGroups.test.ts` | `returns_groups_from_be` | Mock fetch → returns array; hook resolves with data. |
| `useMyGroups.test.ts` | `staleTime_set_to_15s` | Hook config has `staleTime: 15_000`. |
| `GroupCard.test.tsx` | `renders_name_event_date_members` | All 4 fields visible. |
| `GroupCard.test.tsx` | `tap_invokes_onPress` | Tap → onPress called. |
| `GroupCard.test.tsx` | `truncates_long_event_name` | 60-char event name → 1 line of text, ellipsis. |
| `GroupCard.test.tsx` | `archived_shows_pill` | `archived_at != null` → "ARCHIVED" pill visible. |
| `GroupsList.test.tsx` | `empty_state_when_no_groups` | Empty `groups[]` → empty-state title visible. |
| `GroupsList.test.tsx` | `renders_one_card_per_group` | 3 groups → 3 cards. |
| `GroupsList.test.tsx` | `cta_create_navigates_to_create` | Tap CTA → navigate called with `create`. |
| `GroupsList.test.tsx` | `cta_join_navigates_to_join` | Tap → navigate `join`. |
| `GroupsList.test.tsx` | `pull_to_refresh_invalidates_query` | RefreshControl invoked → queryClient invalidate called. |
| `GroupsList.test.tsx` | `hero_gradient_rotates_through_HUES` | First card uses `HUES[0]`; 7th uses `HUES[0]` (mod). |
| `GroupsList.test.tsx` | `error_state_shows_retry` | Mock query error → "Couldn't load groups" + retry visible. |

**Manual QA — DARK MODE ONLY (OQ-04):**

1. Auth as fresh user → empty state.
2. Create a group (FE-002) → return to Home → 1 card.
3. Join another group via invite code → 2 cards, different HUES.
4. Pull down → spinner → cards re-render.
5. Kill network → cards still render from cache; offline badge appears.
6. Visual parity check vs prototype `isGroups` block:
   - Title "GROUPS" uses gradient.title.
   - Subtitle "Pick sets together. See who's where."
   - Card layout (hero + meta rows) matches.
   - CTA gradient matches.

**Structured-log lines:** N/A.

**Failure modes:**

- `useMyGroups` 401 → AuthStack mounts.
- Other errors → retry available.

## 8. Out of scope

| Item | Where |
|---|---|
| Search / filter groups | OQ-01 — Search tab is placeholder; if implemented later, BACKLOG-021. |
| Group rename inline from this screen | FE-005 (settings inside group detail). |
| Multi-select / archive | v2. |
| Light theme | BACKLOG-001. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. Home tab shows placeholder text; users can still navigate to FE-002/FE-004 via deep link if any. Wave-3 backslidey.
