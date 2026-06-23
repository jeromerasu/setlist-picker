# Overnight Status — 2026-06-23

## Summary

Full v1 MVP shipped across three waves in one session continuation.

---

## Bundle 6 — Wave 3 FE Screens (9 tickets)

All 9 tickets committed to `design/initial-schema`, pushed to remote. PR #2 absorbs everything.

| Ticket | SHA | Description | Tests delta | Notes |
|---|---|---|---|---|
| FE-001 | `35e36f5` | Groups list — GroupsList + GroupCard + useMyGroups + HomeStack | +13 | api.ts rewritten to match actual BE Pydantic shapes |
| FE-002 | `b98cf1c` | Create group form — useCreateGroup mutation + nav | +8 | event_not_found 404 clears event selection |
| FE-003 | `0097391` | Event picker — debounced useEvents + mono-letter tiles | +13 | deriveMono + deriveTileGradient (djb2 hash) |
| FE-004 | `eac5afb` | Join group — Crockford B32 normalization (I→1, L→1, O→0) | +13 | normalizeCode clips to 8 chars; 404 shows inline error |
| FE-005 | `b5b0557` | Group detail — day-bucketed lineup + pick toggle + nav | +12 | usePickToggle POST/DELETE; pickedSetIds takes optional memberId |
| FE-006 | `7a249f3` | Schedule — dual-scroll grid + day tabs + useUpNext | +18 | HOUR_HEIGHT=64px; DayMenu + Timeline overlay (pointer-events none) |
| FE-007 | `c34739a` | Artist detail — cyber-retro aesthetic + audio preview | +9 | expo-av stubbed (not installed); ArtistDetailResponse uses artist_name + top_track (singular) |
| FE-008 | `c75656e` | Right-now snapshot — stages→sets flattened + share | +6 | react-native-view-shot stubbed; AvatarStack initials from display_name |
| FE-009 | `3568a4f` | Account profile — color picker + group leave + sign out | +10 | Replaces YouPlaceholder in BottomTabs |

**Total Bundle 6 tests: 102 new tests**

---

## Full Suite at End of Session

```
Test Suites: 27 passed, 27 total
Tests:       147 passed, 147 total
Snapshots:   21 passed, 21 total
```

tsc --noEmit: CLEAN

---

## Deviations from Spec

1. **FE-007 `ArtistDetailResponse`**: Spec assumed `name`, `bio`, `top_tracks[]`, `artist_id`. Actual BE shape is `artist_name`, `top_track` (singular, no bio, no track IDs). Adapted screen and tests to match real API.

2. **`AvatarStack` interface**: Expects `{ initials, color }` not `{ member_id, display_name, avatar_color }`. Fixed in both `ArtistRowAll` (djb2 initials from name) and `RightNowSnapshot` (display_name.slice(0,2)).

3. **`expo-av` and `react-native-view-shot`**: Neither package is installed. Both stubbed via `src/types/global.d.ts` (module declarations) + `src/__mocks__/` files + `moduleNameMapper` in package.json. Audio preview and screenshot share are stub-ready for Wave 4.

4. **`PickSummary` shape**: Actual shape is `{ member_id, set_id, state, state_clock_ms }` — not the design-doc shape. `dayBuckets.ts` and all tests updated to match.

5. **FE-006 AllStagesGrid `groupByStage`**: Groups by first artist name (not a formal stage entity from the API, since the lineup endpoint returns `SetDetail[]` without stage grouping). Stage assignment may need revisiting when the schedule endpoint has explicit stage data.

---

## Wave Coverage

| Wave | Scope | Status |
|---|---|---|
| Wave 1 BE (BE-001–BE-011) | Core group/event/picks | ✅ Shipped (prior session) |
| Wave 2 BE (BE-012–BE-020) | Auth, artists, snapshot | ✅ Shipped (prior session) |
| Wave 2 FE (FE-100–FE-102) | Expo init + auth flow | ✅ Shipped (prior session) |
| Wave 3 FE (FE-001–FE-009) | All screens | ✅ Shipped this session |

---

## What's Left for v1

Per the Epic, the v1 MVP is complete at code level. Remaining steps:

- [ ] OQ-03 lock: TML 2026 W2 is seeded as the only event — confirm seed is in Alembic migration
- [ ] Apple Sign-In stub (ADR-006) — `useAppleSignIn.ts` already stubbed in FE-102
- [ ] Install `expo-av` + `react-native-view-shot` when audio preview / screenshot share goes live
- [ ] CI green on `design/initial-schema` branch

---

Generated: 2026-06-23 (end of overnight session)
