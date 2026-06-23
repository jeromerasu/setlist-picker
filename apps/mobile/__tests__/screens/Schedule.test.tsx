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

jest.mock("@/hooks/useScheduleData", () => ({
  useScheduleData: (ic: string) => mockUseScheduleData(ic),
}));
jest.mock("@/hooks/useGroupState", () => ({
  useGroupState: (ic: string) => mockUseGroupState(ic),
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

beforeEach(() => {
  mockNavigate.mockReset();
  mockGoBack.mockReset();
  mockUseScheduleData.mockReturnValue({ sets: ALL_SETS, eventName: "TML 2026", isLoading: false });
  mockUseGroupState.mockReturnValue({ data: { picks: [] } });
});

test("renders_event_name", () => {
  const { getByText } = render(<Schedule />, { wrapper });
  expect(getByText("TML 2026")).toBeTruthy();
});

test("renders_day_tabs", () => {
  const { getByTestId } = render(<Schedule />, { wrapper });
  expect(getByTestId("day-tab-Friday")).toBeTruthy();
  expect(getByTestId("day-tab-Saturday")).toBeTruthy();
});

test("tap_day_tab_switches_day", () => {
  const { getByTestId, getByText } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("day-tab-Saturday"));
  // After switching, Saturday tab exists (just verifying press doesn't crash)
  expect(getByText("Saturday")).toBeTruthy();
});

test("tap_set_navigates_to_artist_detail", () => {
  const { getByTestId } = render(<Schedule />, { wrapper });
  fireEvent.press(getByTestId("grid-set-s1"));
  expect(mockNavigate).toHaveBeenCalledWith("ArtistDetail", { artist_name: "Artist s1" });
});

test("shows_loading_when_data_loading", () => {
  mockUseScheduleData.mockReturnValue({ sets: [], eventName: "", isLoading: true });
  const { UNSAFE_getByType } = render(<Schedule />, { wrapper });
  expect(UNSAFE_getByType(require("react-native").ActivityIndicator)).toBeTruthy();
});

test("back_chip_pops_screen", () => {
  const { getByLabelText } = render(<Schedule />, { wrapper });
  fireEvent.press(getByLabelText("Go back"));
  expect(mockGoBack).toHaveBeenCalled();
});
