import React from "react";
import { render, fireEvent, waitFor, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── Navigation ──────────────────────────────────────────────────────────────

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
const mockReplace = jest.fn();
const mockSetParams = jest.fn();

let mockRouteParams: Record<string, unknown> = {};

jest.mock("@react-navigation/native", () => {
  const RN = require("react-native");
  return {
    useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack, replace: mockReplace, setParams: mockSetParams }),
    useRoute: () => ({ params: mockRouteParams }),
    NavigationContainer: ({ children }: { children: unknown }) =>
      require("react").createElement(RN.View, null, children),
  };
});

jest.mock("@react-navigation/native-stack", () => ({
  createNativeStackNavigator: () => ({
    Navigator: ({ children }: { children: unknown }) =>
      require("react").createElement(require("react-native").View, null, children),
    Screen: () => null,
  }),
}));

// ─── Hook mock ───────────────────────────────────────────────────────────────

const mockMutate = jest.fn();
const mockInvalidate = jest.fn();

jest.mock("@/hooks/useCreateGroup", () => ({
  useCreateGroup: () => ({ mutate: mockMutate, isPending: false, error: null }),
}));

jest.mock("@tanstack/react-query", () => {
  const actual = jest.requireActual("@tanstack/react-query");
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries: mockInvalidate }),
  };
});

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Subject ─────────────────────────────────────────────────────────────────

import { CreateGroup } from "@/screens/groups/CreateGroup";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockMutate.mockReset();
  mockInvalidate.mockReset();
  mockRouteParams = {};
});

test("renders_name_input_and_event_button", () => {
  const { getByTestId } = render(<CreateGroup />, { wrapper });
  expect(getByTestId("name-input")).toBeTruthy();
  expect(getByTestId("event-btn")).toBeTruthy();
});

test("submit_disabled_initially", () => {
  const { getByTestId } = render(<CreateGroup />, { wrapper });
  const btn = getByTestId("submit-btn");
  expect(btn.props.accessibilityState?.disabled ?? btn.props.disabled).toBeTruthy();
});

test("submit_enabled_when_name_and_event_present", () => {
  mockRouteParams = { selectedEvent: { event_id: "e1", name: "TML 2026 W2" } };
  const { getByTestId } = render(<CreateGroup />, { wrapper });
  fireEvent.changeText(getByTestId("name-input"), "Ravefam");
  const btn = getByTestId("submit-btn");
  // Enabled = not disabled
  const disabled = btn.props.accessibilityState?.disabled ?? btn.props.disabled;
  expect(disabled).toBeFalsy();
});

test("submit_disabled_when_name_only_whitespace", () => {
  mockRouteParams = { selectedEvent: { event_id: "e1", name: "TML 2026 W2" } };
  const { getByTestId } = render(<CreateGroup />, { wrapper });
  fireEvent.changeText(getByTestId("name-input"), "   ");
  const btn = getByTestId("submit-btn");
  expect(btn.props.accessibilityState?.disabled ?? btn.props.disabled).toBeTruthy();
});

test("event_button_tap_navigates_to_event_picker", () => {
  const { getByTestId } = render(<CreateGroup />, { wrapper });
  fireEvent.press(getByTestId("event-btn"));
  expect(mockNavigate).toHaveBeenCalledWith("EventPicker");
});

test("route_param_selectedEvent_fills_event_label", () => {
  mockRouteParams = { selectedEvent: { event_id: "e1", name: "TML 2026 W2" } };
  const { getByText } = render(<CreateGroup />, { wrapper });
  expect(getByText("TML 2026 W2")).toBeTruthy();
});

test("submit_invokes_useCreateGroup", () => {
  mockRouteParams = { selectedEvent: { event_id: "e1", name: "TML 2026 W2" } };
  const { getByTestId } = render(<CreateGroup />, { wrapper });
  fireEvent.changeText(getByTestId("name-input"), "Ravefam");
  fireEvent.press(getByTestId("submit-btn"));
  expect(mockMutate).toHaveBeenCalledWith(
    { name: "Ravefam", event_id: "e1" },
    expect.any(Object)
  );
});
