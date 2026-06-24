import React from "react";
import { render, fireEvent } from "@testing-library/react-native";
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

const mockUseScheduleData = jest.fn();
const mockUseGroupState = jest.fn();
const mockUseGroupSchedule = jest.fn();
const mockMutatePick = jest.fn();

jest.mock("@/hooks/useScheduleData", () => ({
  useScheduleData: (ic: string) => mockUseScheduleData(ic),
}));
jest.mock("@/hooks/useGroupState", () => ({
  useGroupState: (ic: string) => mockUseGroupState(ic),
}));
jest.mock("@/hooks/useGroupSchedule", () => ({
  useGroupSchedule: (ic: string, day: string) => mockUseGroupSchedule(ic, day),
}));
jest.mock("@/hooks/usePickToggle", () => ({
  usePickToggle: () => ({ mutate: mockMutatePick }),
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Test data ───────────────────────────────────────────────────────────────

import { Schedule } from "@/screens/schedule/Schedule";
import type { GroupSetItem, MemberPickInfo, SetDetail, ArtistRef } from "@/types/api";

function makeSet(id: string, dayLabel: string, startsAt = "2026-07-04T20:00:00Z"): SetDetail {
  const artist: ArtistRef = { artist_id: id, name: `Artist ${id}`, position: 1, spotify_artist_id: null };
  return {
    set_id: id,
    display_name: `Set ${id}`,
    day_label: dayLabel,
    starts_at: startsAt,
    ends_at: "2026-07-04T21:00:00Z",
    artists: [artist],
  };
}

const FRIDAY_SETS = [makeSet("s1", "Friday"), makeSet("s2", "Friday")];
const ALL_SETS = [...FRIDAY_SETS, makeSet("s3", "Saturday")];

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

const SCHEDULE_DATA_DEFAULT = {
  sets: ALL_SETS,
  stages: [],
  stageBySetId: new Map(),
  eventName: "TML 2026",
  myMemberId: undefined,
  isLoading: false,
};

const GROUP_STATE_DEFAULT = {
  data: { picks: [], members: [] },
};

const GROUP_SCHEDULE_EMPTY = { data: { group_id: "g1", event_id: "e1", day_label: "Friday", sets: [] } };

function makeGroupSetItem(setId: string, members: MemberPickInfo[]): GroupSetItem {
  return {
    set_id: setId,
    display_name: `Set ${setId}`,
    stage_name: "Mainstage",
    stage_color_hex: "#ff4f9a",
    day_label: "Friday",
    starts_at: "2026-07-04T20:00:00Z",
    ends_at: "2026-07-04T21:00:00Z",
    going_members: members,
  };
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockGoBack.mockReset();
  mockMutatePick.mockReset();
  mockUseScheduleData.mockReturnValue(SCHEDULE_DATA_DEFAULT);
  mockUseGroupState.mockReturnValue(GROUP_STATE_DEFAULT);
  mockUseGroupSchedule.mockReturnValue(GROUP_SCHEDULE_EMPTY);
});

test("renders_day_picker_button", () => {
  const { getByTestId } = render(<Schedule />, { wrapper });
  expect(getByTestId("day-picker-btn")).toBeTruthy();
});

test("day_picker_shows_day_number", () => {
  const { getByText } = render(<Schedule />, { wrapper });
  // Two days: Friday (index 0 → Day 1) and Saturday (index 1 → Day 2)
  expect(getByText("Day 1")).toBeTruthy();
});

test("tapping_day_picker_opens_dropdown", () => {
  const { getByTestId } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("day-picker-btn"));
  expect(getByTestId("day-menu-backdrop")).toBeTruthy();
  expect(getByTestId("day-option-Friday")).toBeTruthy();
  expect(getByTestId("day-option-Saturday")).toBeTruthy();
});

test("selecting_day_from_dropdown_closes_menu", () => {
  const { getByTestId, queryByTestId } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("day-picker-btn"));
  fireEvent.press(getByTestId("day-option-Saturday"));
  expect(queryByTestId("day-menu-backdrop")).toBeNull();
});

test("all_stages_tab_is_default", () => {
  const { getByTestId } = render(<Schedule />, { wrapper });
  expect(getByTestId("grid-set-s1")).toBeTruthy();
});

test("tap_grid_set_cycles_pick_to_going", () => {
  const { getByTestId } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("grid-set-s1"));
  // none → going: POST via togglePick({ is_picked: false })
  expect(mockMutatePick).toHaveBeenCalledWith(
    expect.objectContaining({ set_id: "s1", is_picked: false, invite_code: "TESTCODE" }),
  );
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("shows_loading_when_data_loading", () => {
  mockUseScheduleData.mockReturnValue({ ...SCHEDULE_DATA_DEFAULT, isLoading: true });
  const { UNSAFE_getByType } = render(<Schedule />, { wrapper });
  expect(UNSAFE_getByType(require("react-native").ActivityIndicator)).toBeTruthy();
});

test("back_chip_pops_screen", () => {
  const { getByLabelText } = render(<Schedule />, { wrapper });
  fireEvent.press(getByLabelText("Go back"));
  expect(mockGoBack).toHaveBeenCalled();
});

test("switching_to_schedule_tab_shows_filter_chips", () => {
  const { getByTestId, queryByTestId } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("schedule-tab"));
  expect(queryByTestId("grid-set-s1")).toBeNull();
  expect(getByTestId("mine-filter")).toBeTruthy();
  expect(getByTestId("group-filter")).toBeTruthy();
});

test("mine_filter_with_no_picks_shows_empty_state", () => {
  const { getByTestId, getByText } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("schedule-tab"));
  fireEvent.press(getByTestId("mine-filter"));
  expect(getByText("Pick your first set")).toBeTruthy();
});

// ─── REALIGN-007: group schedule BE integration tests ────────────────────────

test("group_filter_shows_sets_from_group_schedule_endpoint", () => {
  const member: MemberPickInfo = { member_id: "m1", display_name: "Jerome", avatar_color: "#a78bfa" };
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", [member])],
    },
  });

  const { getByTestId } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("schedule-tab"));
  fireEvent.press(getByTestId("group-filter"));

  // s1 is in the group schedule → timeline-set-s1 should appear
  expect(getByTestId("timeline-set-s1")).toBeTruthy();
});

test("group_filter_going_count_uses_going_members_length_from_api", () => {
  const members: MemberPickInfo[] = [
    { member_id: "m1", display_name: "Jerome", avatar_color: "#a78bfa" },
    { member_id: "m2", display_name: "Alex", avatar_color: "#36c6ff" },
  ];
  mockUseGroupSchedule.mockReturnValue({
    data: {
      group_id: "g1",
      event_id: "e1",
      day_label: "Friday",
      sets: [makeGroupSetItem("s1", members)],
    },
  });

  const { getByTestId, getByText } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("schedule-tab"));
  fireEvent.press(getByTestId("group-filter"));

  // 2 going_members → "2 going"
  expect(getByText("2 going")).toBeTruthy();
});

test("group_filter_shows_empty_state_when_group_schedule_returns_no_sets", () => {
  mockUseGroupSchedule.mockReturnValue({
    data: { group_id: "g1", event_id: "e1", day_label: "Friday", sets: [] },
  });

  const { getByTestId, getByText } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("schedule-tab"));
  fireEvent.press(getByTestId("group-filter"));

  expect(getByText("No Group Sets Yet")).toBeTruthy();
});

test("group_filter_stage_color_uses_stage_color_hex_from_api", () => {
  const member: MemberPickInfo = { member_id: "m1", display_name: "Jerome", avatar_color: "#a78bfa" };
  const gsItem: GroupSetItem = {
    ...makeGroupSetItem("s1", [member]),
    stage_color_hex: "#aabbcc",
    stage_name: "Ranch Stage",
  };
  mockUseGroupSchedule.mockReturnValue({
    data: { group_id: "g1", event_id: "e1", day_label: "Friday", sets: [gsItem] },
  });

  const { getByTestId } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("schedule-tab"));
  fireEvent.press(getByTestId("group-filter"));

  expect(getByTestId("timeline-set-s1")).toBeTruthy();
});
