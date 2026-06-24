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
const mockMutatePick = jest.fn();

jest.mock("@/hooks/useScheduleData", () => ({
  useScheduleData: (ic: string) => mockUseScheduleData(ic),
}));
jest.mock("@/hooks/useGroupState", () => ({
  useGroupState: (ic: string) => mockUseGroupState(ic),
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
import type { SetDetail, ArtistRef } from "@/types/api";

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

beforeEach(() => {
  mockNavigate.mockReset();
  mockGoBack.mockReset();
  mockMutatePick.mockReset();
  mockUseScheduleData.mockReturnValue(SCHEDULE_DATA_DEFAULT);
  mockUseGroupState.mockReturnValue(GROUP_STATE_DEFAULT);
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

test("tap_set_navigates_to_artist_detail", () => {
  const { getByTestId } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("grid-set-s1"));
  expect(mockNavigate).toHaveBeenCalledWith("ArtistDetail", { artist_name: "Artist s1" });
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
