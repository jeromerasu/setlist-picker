import React from "react";
import { render, fireEvent, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── Navigation ──────────────────────────────────────────────────────────────

const mockReplace = jest.fn();
const mockGoBack = jest.fn();

jest.mock("@react-navigation/native", () => {
  const RN = require("react-native");
  return {
    useNavigation: () => ({ replace: mockReplace, goBack: mockGoBack }),
    NavigationContainer: ({ children }: { children: unknown }) =>
      require("react").createElement(RN.View, null, children),
  };
});

// ─── Hook mock ───────────────────────────────────────────────────────────────

const mockMutate = jest.fn();
let mockIsPending = false;

jest.mock("@/hooks/useJoinGroup", () => ({
  useJoinGroup: () => ({ mutate: mockMutate, isPending: mockIsPending }),
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Subject ─────────────────────────────────────────────────────────────────

import { JoinGroup } from "@/screens/groups/JoinGroup";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  mockReplace.mockReset();
  mockGoBack.mockReset();
  mockMutate.mockReset();
  mockIsPending = false;
});

test("renders_code_input_and_disabled_submit", () => {
  const { getByTestId } = render(<JoinGroup />, { wrapper });
  expect(getByTestId("code-input")).toBeTruthy();
  expect(getByTestId("submit-btn").props.accessibilityState?.disabled).toBe(true);
});

test("submit_enabled_when_code_is_8_chars", () => {
  const { getByTestId } = render(<JoinGroup />, { wrapper });
  fireEvent.changeText(getByTestId("code-input"), "K7M2X9PQ");
  expect(getByTestId("submit-btn").props.accessibilityState?.disabled).toBeFalsy();
});

test("submit_disabled_when_code_under_8_chars", () => {
  const { getByTestId } = render(<JoinGroup />, { wrapper });
  fireEvent.changeText(getByTestId("code-input"), "K7M2X9");
  expect(getByTestId("submit-btn").props.accessibilityState?.disabled).toBe(true);
});

test("normalizes_I_and_O_in_code_input", () => {
  const { getByTestId } = render(<JoinGroup />, { wrapper });
  fireEvent.changeText(getByTestId("code-input"), "IO123456");
  expect(getByTestId("code-input").props.value).toBe("10123456");
});

test("back_chip_calls_goBack", () => {
  const { getByLabelText } = render(<JoinGroup />, { wrapper });
  fireEvent.press(getByLabelText("Go back"));
  expect(mockGoBack).toHaveBeenCalled();
});

test("submit_calls_mutate_with_normalized_code", () => {
  const { getByTestId } = render(<JoinGroup />, { wrapper });
  fireEvent.changeText(getByTestId("code-input"), "K7M2X9PQ");
  fireEvent.press(getByTestId("submit-btn"));
  expect(mockMutate).toHaveBeenCalledWith(
    { invite_code: "K7M2X9PQ" },
    expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) })
  );
});

test("on_success_navigates_to_group_detail", () => {
  const { getByTestId } = render(<JoinGroup />, { wrapper });
  fireEvent.changeText(getByTestId("code-input"), "K7M2X9PQ");
  fireEvent.press(getByTestId("submit-btn"));

  const call = mockMutate.mock.calls[0];
  call[1].onSuccess({ group: { invite_code: "K7M2X9PQ" } });
  expect(mockReplace).toHaveBeenCalledWith("GroupDetail", { invite_code: "K7M2X9PQ" });
});

test("on_404_shows_error_message", () => {
  const { getByTestId, getByText } = render(<JoinGroup />, { wrapper });
  fireEvent.changeText(getByTestId("code-input"), "BADCODE1");
  fireEvent.press(getByTestId("submit-btn"));

  const call = mockMutate.mock.calls[0];
  act(() => { call[1].onError({ statusCode: 404 }); });
  expect(getByText(/invalid or expired/)).toBeTruthy();
});
