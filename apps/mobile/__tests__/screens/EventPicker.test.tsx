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
    NavigationContainer: ({ children }: { children: unknown }) =>
      require("react").createElement(RN.View, null, children),
  };
});

// ─── Hook mock ───────────────────────────────────────────────────────────────

const mockUseEvents = jest.fn();
jest.mock("@/hooks/useEvents", () => ({ useEvents: (q: string) => mockUseEvents(q) }));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Subject ─────────────────────────────────────────────────────────────────

import { EventPicker } from "@/screens/groups/EventPicker";
import type { EventListItem } from "@/types/api";

function makeEvent(i: number): EventListItem {
  return {
    event_id: `e${i}`,
    name: `Event ${i}`,
    start_date: "2026-07-01",
    end_date: "2026-07-03",
    location: "Las Vegas",
    timezone: "America/Los_Angeles",
  };
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockGoBack.mockReset();
  mockUseEvents.mockReset();
});

test("renders_all_events_initially", () => {
  mockUseEvents.mockReturnValue({ data: { events: Array.from({ length: 7 }, (_, i) => makeEvent(i)) }, isLoading: false });
  const { getAllByTestId } = render(<EventPicker />, { wrapper });
  expect(getAllByTestId(/^event-row-/).length).toBe(7);
});

test("filters_on_search", () => {
  const events = [makeEvent(0), makeEvent(1)];
  // Initially 2 events
  mockUseEvents.mockReturnValue({ data: { events }, isLoading: false });
  const { getByTestId, getAllByTestId } = render(<EventPicker />, { wrapper });
  expect(getAllByTestId(/^event-row-/).length).toBe(2);
  // After typing, hook is called again (new query); test just verifies the input triggers a call
  fireEvent.changeText(getByTestId("search-input"), "edc");
  expect(mockUseEvents).toHaveBeenCalledWith("edc");
});

test("empty_result_shows_no_match_message", () => {
  // Start with results, then simulate no-match after typing a query
  mockUseEvents.mockReturnValue({ data: { events: [] }, isLoading: false });
  const { getByText, getByTestId } = render(<EventPicker />, { wrapper });
  fireEvent.changeText(getByTestId("search-input"), "zzz");
  // After typing, query state = "zzz" and events is still [] from mock
  // The EmptyState title contains the query string
  expect(getByText(/No festivals match/)).toBeTruthy();
});

test("tap_event_navigates_back_with_payload", () => {
  const event = makeEvent(0);
  mockUseEvents.mockReturnValue({ data: { events: [event] }, isLoading: false });
  const { getByTestId } = render(<EventPicker />, { wrapper });
  fireEvent.press(getByTestId("event-row-e0"));
  expect(mockNavigate).toHaveBeenCalledWith("CreateGroup", {
    selectedEvent: { event_id: "e0", name: "Event 0" },
  });
});

test("back_chip_pops_without_selection", () => {
  mockUseEvents.mockReturnValue({ data: { events: [] }, isLoading: false });
  const { getByLabelText } = render(<EventPicker />, { wrapper });
  fireEvent.press(getByLabelText("Go back"));
  expect(mockGoBack).toHaveBeenCalled();
  expect(mockNavigate).not.toHaveBeenCalled();
});
