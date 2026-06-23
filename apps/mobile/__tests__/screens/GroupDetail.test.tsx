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
const mockUseEventLineup = jest.fn();
const mockTogglePick = jest.fn();

jest.mock("@/hooks/useGroupState", () => ({ useGroupState: (ic: string) => mockUseGroupState(ic) }));
jest.mock("@/hooks/useEventLineup", () => ({ useEventLineup: (id: string) => mockUseEventLineup(id) }));
jest.mock("@/hooks/usePickToggle", () => ({
  usePickToggle: () => ({ mutate: mockTogglePick, isPending: false }),
}));

jest.mock("@/utils/inviteShare", () => ({
  shareInvite: jest.fn(async () => undefined),
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Test data ───────────────────────────────────────────────────────────────

import { GroupDetail } from "@/screens/groups/GroupDetail";
import type { GroupStateResponse, SetDetail, ArtistRef } from "@/types/api";

function makeArtist(id: string): ArtistRef {
  return { artist_id: id, name: `Artist ${id}`, position: 1, spotify_artist_id: null };
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

const MOCK_GROUP: GroupStateResponse = {
  group_id: "g1",
  invite_code: "TESTCODE",
  name: "Test Group",
  event: { event_id: "ev1", name: "TML 2026", start_date: "2026-07-04", end_date: "2026-07-07", location: null, timezone: "America/Chicago" },
  members: [],
  picks: [],
  archived_at: null,
  last_active_at: "2026-07-01T00:00:00Z",
};

const MOCK_SETS = [makeSet("s1", "Friday"), makeSet("s2", "Friday"), makeSet("s3", "Saturday")];

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockGoBack.mockReset();
  mockTogglePick.mockReset();
  mockUseGroupState.mockReturnValue({ data: MOCK_GROUP, isLoading: false, error: null });
  mockUseEventLineup.mockReturnValue({ data: { event_id: "ev1", sets: MOCK_SETS } });
});

test("renders_group_name_and_code", () => {
  const { getByText } = render(<GroupDetail />, { wrapper });
  expect(getByText("Test Group")).toBeTruthy();
  expect(getByText("TESTCODE")).toBeTruthy();
});

test("renders_day_buckets", () => {
  const { getAllByText } = render(<GroupDetail />, { wrapper });
  expect(getAllByText("Friday").length).toBeGreaterThan(0);
  expect(getAllByText("Saturday").length).toBeGreaterThan(0);
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

test("tap_pick_btn_calls_toggle_with_correct_args", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("pick-btn-s1"));
  expect(mockTogglePick).toHaveBeenCalledWith({
    invite_code: "TESTCODE",
    set_id: "s1",
    is_picked: false,
  });
});

test("tap_artist_navigates_to_artist_detail", () => {
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  fireEvent.press(getByTestId("artist-row-s1"));
  expect(mockNavigate).toHaveBeenCalledWith("ArtistDetail", { artist_name: "Artist s1" });
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

test("picked_set_shows_filled_heart", () => {
  const group = {
    ...MOCK_GROUP,
    picks: [{
      set_id: "s1",
      member_id: "m1",
      state: "picked",
      state_clock_ms: 0,
    }],
  };
  mockUseGroupState.mockReturnValue({ data: group, isLoading: false, error: null });
  const { getByTestId } = render(<GroupDetail />, { wrapper });
  const btn = getByTestId("pick-btn-s1");
  const textNodes = btn.findAllByType(require("react-native").Text);
  const heartNode = textNodes.find((n: { props: { children: unknown } }) => n.props.children === "♥" || n.props.children === "♡");
  expect(heartNode?.props.children).toBe("♥");
});
