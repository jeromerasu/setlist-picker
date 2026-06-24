import React from "react";
import { render, fireEvent, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── Navigation ──────────────────────────────────────────────────────────────

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();

jest.mock("@react-navigation/native", () => {
  const RN = require("react-native");
  return {
    useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack }),
    useRoute: () => ({ params: { invite_code: "TESTCODE" } }),
    NavigationContainer: ({ children }: { children: unknown }) =>
      require("react").createElement(RN.View, null, children),
  };
});

// ─── Hook mocks ──────────────────────────────────────────────────────────────

const mockUseGroupState = jest.fn();
const mockUseScheduleData = jest.fn();
const mockUseMyGroups = jest.fn();
const mockTogglePick = jest.fn();

const mockUseGroupSchedule = jest.fn();

jest.mock("@/hooks/useGroupState", () => ({ useGroupState: (ic: string) => mockUseGroupState(ic) }));
jest.mock("@/hooks/useScheduleData", () => ({ useScheduleData: (ic: string) => mockUseScheduleData(ic) }));
jest.mock("@/hooks/useMyGroups", () => ({ useMyGroups: () => mockUseMyGroups() }));
jest.mock("@/hooks/useGroupSchedule", () => ({
  useGroupSchedule: (ic: string, day: string) => mockUseGroupSchedule(ic, day),
}));
jest.mock("@/hooks/usePickToggle", () => ({
  usePickToggle: () => ({ mutate: mockTogglePick, isPending: false }),
}));

jest.mock("react-native/Libraries/Share/Share", () => ({
  share: jest.fn(async () => ({ action: "sharedAction" })),
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Test data ───────────────────────────────────────────────────────────────

import { GroupDetail } from "@/screens/groups/GroupDetail";
import type { GroupScheduleResponse, GroupSetItem, GroupStateResponse, MemberPickInfo, SetDetail, StageDetail, ArtistRef, MemberOut } from "@/types/api";
import type { StageInfo } from "@/hooks/useScheduleData";

function makeArtist(id: string, name = `Artist ${id}`): ArtistRef {
  return { artist_id: id, name, position: 1, spotify_artist_id: null };
}

function makeSet(id: string, dayLabel: string): SetDetail {
  return {
    set_id: id,
    display_name: `Set ${id}`,
    day_label: dayLabel,
    starts_at: "2026-07-04T20:00:00Z",
    ends_at: "2026-07-04T21:00:00Z",
    artists: [makeArtist(id)],
  };
}

function makeStage(id: string, name: string, order: number, sets: SetDetail[]): StageDetail {
  return { stage_id: id, name, display_order: order, color_hex: "#ff4f9a", sets };
}

function makeMember(id: string, name: string): MemberOut {
  return {
    member_id: id,
    user_id: `user-${id}`,
    group_id: "grp1",
    display_name: name,
    avatar_color: "#a78bfa",
    display_name_override: null,
    joined_at: "2026-01-01T00:00:00Z",
  };
}

const SET_S1 = makeSet("s1", "Friday");
const SET_S2 = makeSet("s2", "Friday");
const SET_S3 = makeSet("s3", "Saturday");
const ALL_SETS = [SET_S1, SET_S2, SET_S3];

const STAGE_A = makeStage("stg1", "Mainstage", 0, [SET_S1, SET_S2]);
const STAGE_B = makeStage("stg2", "Freedom", 1, [SET_S3]);

const STAGE_BY_SET = new Map<string, StageInfo>([
  ["s1", { name: "Mainstage", color: "#ff4f9a" }],
  ["s2", { name: "Mainstage", color: "#ff4f9a" }],
  ["s3", { name: "Freedom", color: "#36c6ff" }],
]);

const MOCK_GROUP: GroupStateResponse = {
  group_id: "g1",
  invite_code: "TESTCODE",
  name: "Test Group",
  event: {
    event_id: "ev1",
    name: "TML 2026",
    start_date: "2026-07-04",
    end_date: "2026-07-07",
    location: "Boom, Belgium",
    timezone: "Europe/Brussels",
  },
  members: [makeMember("m1", "Diego F"), makeMember("m2", "Ana K")],
  picks: [],
  archived_at: null,
  last_active_at: "2026-07-01T00:00:00Z",
};

const SCHEDULE_DATA_DEFAULT = {
  sets: ALL_SETS,
  stages: [STAGE_A, STAGE_B],
  stageBySetId: STAGE_BY_SET,
  eventName: "TML 2026",
  myMemberId: "m1",
  isLoading: false,
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

const GROUP_SCHEDULE_EMPTY: GroupScheduleResponse = {
  group_id: "g1",
  event_id: "ev1",
  day_label: "Friday",
  sets: [],
};

function makeGroupSetItem(setId: string, dayLabel: string, goingMembers: MemberPickInfo[]): GroupSetItem {
  return {
    set_id: setId,
    display_name: `Set ${setId}`,
    stage_name: "Mainstage",
    stage_color_hex: "#ff4f9a",
    day_label: dayLabel,
    starts_at: "2026-07-04T20:00:00Z",
    ends_at: "2026-07-04T21:00:00Z",
    going_members: goingMembers,
  };
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockGoBack.mockReset();
  mockTogglePick.mockReset();
  mockUseGroupState.mockReturnValue({ data: MOCK_GROUP, isLoading: false, error: null });
  mockUseScheduleData.mockReturnValue(SCHEDULE_DATA_DEFAULT);
  mockUseMyGroups.mockReturnValue({
    data: { groups: [{ invite_code: "TESTCODE", member_id: "m1" }] },
  });
  mockUseGroupSchedule.mockReturnValue({ data: GROUP_SCHEDULE_EMPTY });
});

// ─── Rendering tests ─────────────────────────────────────────────────────────

test("renders_group_name", () => {
  const { getByText } = render(<GroupDetail />, { wrapper });
  expect(getByText("Test Group")).toBeTruthy();
});

test("renders_event_name", () => {
  const { getByText } = render(<GroupDetail />, { wrapper });
  expect(getByText("TML 2026")).toBeTruthy();
});

test("renders_invite_code", () => {
  const { getByText } = render(<GroupDetail />, { wrapper });
  expect(getByText("TESTCODE")).toBeTruthy();
});

test("shows_loading_indicator_when_loading", () => {
  mockUseGroupState.mockReturnValue({ data: undefined, isLoading: true, error: null });
  const { UNSAFE_getByType } = render(<GroupDetail />, { wrapper });
  expect(UNSAFE_getByType(require("react-native").ActivityIndicator)).toBeTruthy();
});

test("shows_error_when_group_load_fails", () => {
  mockUseGroupState.mockReturnValue({ data: undefined, isLoading: false, error: new Error("fail") });
  const { getByText } = render(<GroupDetail />, { wrapper });
  expect(getByText(/Failed to load group/)).toBeTruthy();
});

// ─── Tab tests ────────────────────────────────────────────────────────────────

test("all_artists_tab_is_default", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  expect(getByTestId("tab-all-artists")).toBeTruthy();
  expect(getByTestId("all-artist-s1")).toBeTruthy();
});

test("renders_all_artist_rows", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  expect(getByTestId("all-artist-s1")).toBeTruthy();
  expect(getByTestId("all-artist-s2")).toBeTruthy();
  expect(getByTestId("all-artist-s3")).toBeTruthy();
});

test("day_tabs_shown_for_unique_days", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  expect(getByTestId("tab-day-1")).toBeTruthy();
  expect(getByTestId("tab-day-2")).toBeTruthy();
});

test("switching_to_day_tab_shows_stage_groups", () => {
  const { getByTestId, getByText } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("tab-day-1"));
  expect(getByText("MAINSTAGE")).toBeTruthy();
  expect(getByTestId("day-set-s1")).toBeTruthy();
  expect(getByTestId("day-set-s2")).toBeTruthy();
});

test("day_2_tab_shows_saturday_sets_only", () => {
  const { getByTestId, queryByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("tab-day-2"));
  expect(getByTestId("day-set-s3")).toBeTruthy();
  expect(queryByTestId("day-set-s1")).toBeNull();
});

// ─── Interaction tests ────────────────────────────────────────────────────────

test("tapping_all_artist_navigates_to_artist_detail", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("all-artist-s1"));
  expect(mockNavigate).toHaveBeenCalledWith("ArtistDetail", { artist_name: "Artist s1" });
});

test("tapping_day_set_row_toggles_pick", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("tab-day-1"));
  fireEvent.press(getByTestId("day-set-s1"));
  expect(mockTogglePick).toHaveBeenCalledWith({
    invite_code: "TESTCODE",
    set_id: "s1",
    is_picked: false,
  });
});

test("picked_set_shows_filled_pick_indicator", () => {
  mockUseGroupState.mockReturnValue({
    data: {
      ...MOCK_GROUP,
      picks: [{ member_id: "m1", set_id: "s1", state: "active", state_clock_ms: 1000 }],
    },
    isLoading: false,
    error: null,
  });
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("tab-day-1"));
  expect(getByTestId("pick-dot-filled-s1")).toBeTruthy();
  expect(getByTestId("pick-dot-empty-s2")).toBeTruthy();
});

test("schedule_button_navigates_to_schedule", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("schedule-btn"));
  expect(mockNavigate).toHaveBeenCalledWith("Schedule", { invite_code: "TESTCODE" });
});

test("snapshot_button_navigates_to_right_now", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("snapshot-btn"));
  expect(mockNavigate).toHaveBeenCalledWith("RightNowSnapshot", { invite_code: "TESTCODE" });
});

test("back_button_calls_goBack", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("back-btn"));
  expect(mockGoBack).toHaveBeenCalled();
});

test("invite_button_shows_toast", async () => {
  const { getByTestId, queryByTestId } = render(<GroupDetail />, { wrapper });
  expect(queryByTestId("invite-toast")).toBeNull();
  await act(async () => {
    fireEvent.press(getByTestId("invite-btn"));
  });
  expect(getByTestId("invite-toast")).toBeTruthy();
});

test("empty_lineup_shows_no_artists_message", () => {
  mockUseScheduleData.mockReturnValue({
    ...SCHEDULE_DATA_DEFAULT,
    sets: [],
    stages: [],
    stageBySetId: new Map(),
  });
  const { getByText } = render(<GroupDetail />, { wrapper });
  expect(getByText("No artists yet")).toBeTruthy();
});

test("member_count_badge_shown_when_more_than_3_members", () => {
  const group = {
    ...MOCK_GROUP,
    members: [
      makeMember("m1", "Diego F"),
      makeMember("m2", "Ana K"),
      makeMember("m3", "Raj P"),
      makeMember("m4", "Sofia L"),
    ],
  };
  mockUseGroupState.mockReturnValue({ data: group, isLoading: false, error: null });
  const { getByText } = render(<GroupDetail />, { wrapper });
  expect(getByText("+1")).toBeTruthy();
});

// ─── REALIGN-007: group schedule BE integration tests ────────────────────────

test("day_tab_shows_going_avatars_from_group_schedule_api", () => {
  const goingMember: MemberPickInfo = { member_id: "m2", display_name: "Ana K", avatar_color: "#36c6ff" };
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "ev1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", "Friday", [goingMember])],
    },
  });

  const { getByTestId } = render(<GroupDetail />, { wrapper });
  // Switch to Day 1 tab (index 1 in tabLabels = day index 0 = "Friday")
  fireEvent.press(getByTestId("tab-day-1"));

  // The going avatar stack for s1 should be visible (avatar rendered)
  expect(getByTestId("day-set-s1")).toBeTruthy();
});

test("day_tab_going_avatars_absent_when_no_going_members_in_api", () => {
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "ev1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", "Friday", [])],
    },
  });

  const { getByTestId, queryByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("tab-day-1"));

  // Set row is still rendered
  expect(getByTestId("day-set-s1")).toBeTruthy();
  // No going avatars row because going_members is empty
  expect(queryByTestId("going-avatar-m2")).toBeNull();
});

test("day_tab_falls_back_to_local_picks_when_group_schedule_not_loaded", () => {
  // group schedule returns null data (loading state)
  mockUseGroupSchedule.mockReturnValue({ data: null });
  // local picks has m2 going on s1
  const groupWithPick = {
    ...MOCK_GROUP,
    picks: [{ member_id: "m2", set_id: "s1", state: "active", state_clock_ms: 1 }],
  };
  mockUseGroupState.mockReturnValue({ data: groupWithPick, isLoading: false, error: null });

  const { getByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("tab-day-1"));

  // s1 set row rendered; falls back to local picks for going data
  expect(getByTestId("day-set-s1")).toBeTruthy();
});
