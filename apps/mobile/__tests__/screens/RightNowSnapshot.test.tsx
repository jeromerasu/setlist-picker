import React from "react";
import { render, fireEvent } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── Navigation ──────────────────────────────────────────────────────────────

const mockGoBack = jest.fn();

jest.mock("@react-navigation/native", () => {
  const RN = require("react-native");
  return {
    useNavigation: () => ({ goBack: mockGoBack }),
    useRoute: () => ({ params: { invite_code: "SNAP001" } }),
    NavigationContainer: ({ children }: { children: unknown }) =>
      require("react").createElement(RN.View, null, children),
  };
});

// ─── Hook mocks ──────────────────────────────────────────────────────────────

const mockUseSnapshot = jest.fn();

jest.mock("@/hooks/useSnapshot", () => ({ useSnapshot: (ic: string, at?: string) => mockUseSnapshot(ic, at) }));
jest.mock("@/utils/captureScreenshot", () => ({ captureAndShare: jest.fn(async () => undefined) }));
jest.mock("react-native-view-shot", () => {
  const { View } = require("react-native");
  return { default: View };
});
jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Test data ───────────────────────────────────────────────────────────────

import { RightNowSnapshot } from "@/screens/snapshot/RightNowSnapshot";
import type { GroupSnapshotResponse, SnapshotMember } from "@/types/api";

function makePicker(id: string): SnapshotMember {
  return { user_id: `u${id}`, member_id: `m${id}`, display_name: `User ${id}`, avatar_color: "#aaa" };
}

const MOCK_SNAPSHOT: GroupSnapshotResponse = {
  group_id: "g1",
  invite_code: "SNAP001",
  group_name: "Festival Crew",
  event_id: "ev1",
  event_name: "TML 2026",
  timezone: "Europe/Brussels",
  snapshot_at: "2026-07-06T14:00:00Z",
  window_minutes: 60,
  members_total: 3,
  stages: [
    {
      stage_id: "st1",
      name: "Freedom",
      display_order: 1,
      sets: [
        {
          set_id: "s1",
          display_name: "Above & Beyond",
          artist_names: ["Above & Beyond"],
          day_label: "Sunday",
          starts_at: "2026-07-06T14:00:00Z",
          ends_at: "2026-07-06T15:30:00Z",
          pickers: [makePicker("1"), makePicker("2")],
        },
      ],
    },
  ],
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  mockGoBack.mockReset();
  mockUseSnapshot.mockReturnValue({ data: MOCK_SNAPSHOT, isLoading: false, error: null });
});

test("renders_group_name_in_header", () => {
  const { getByTestId } = render(<RightNowSnapshot />, { wrapper });
  expect(getByTestId("snapshot-group-name").props.children).toBe("Festival Crew");
});

test("renders_snapshot_set_rows", () => {
  const { getByTestId } = render(<RightNowSnapshot />, { wrapper });
  expect(getByTestId("snapshot-set-s1")).toBeTruthy();
});

test("shows_loading_indicator_when_loading", () => {
  mockUseSnapshot.mockReturnValue({ data: undefined, isLoading: true, error: null });
  const { UNSAFE_getByType } = render(<RightNowSnapshot />, { wrapper });
  expect(UNSAFE_getByType(require("react-native").ActivityIndicator)).toBeTruthy();
});

test("shows_error_when_snapshot_unavailable", () => {
  mockUseSnapshot.mockReturnValue({ data: undefined, isLoading: false, error: new Error("fail") });
  const { getByText } = render(<RightNowSnapshot />, { wrapper });
  expect(getByText(/Snapshot unavailable/)).toBeTruthy();
});

test("back_chip_calls_goBack", () => {
  const { getByLabelText } = render(<RightNowSnapshot />, { wrapper });
  fireEvent.press(getByLabelText("Go back"));
  expect(mockGoBack).toHaveBeenCalled();
});

test("empty_state_shown_when_no_sets", () => {
  const empty = { ...MOCK_SNAPSHOT, stages: [] };
  mockUseSnapshot.mockReturnValue({ data: empty, isLoading: false, error: null });
  const { getByText } = render(<RightNowSnapshot />, { wrapper });
  expect(getByText(/No picks in the next/)).toBeTruthy();
});
