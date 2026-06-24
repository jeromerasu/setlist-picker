import React from "react";
import { render, fireEvent, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── Hook mocks ──────────────────────────────────────────────────────────────

const mockSaveProfile = jest.fn();
const mockLeaveGroup = jest.fn();
const mockSignOut = jest.fn(async () => undefined);
let mockSaving = false;
let mockLeaving = false;

jest.mock("@/hooks/useUpdateProfile", () => ({
  useUpdateProfile: () => ({ mutate: mockSaveProfile, isPending: mockSaving }),
}));
jest.mock("@/hooks/useLeaveGroup", () => ({
  useLeaveGroup: () => ({ mutate: mockLeaveGroup, isPending: mockLeaving }),
}));
jest.mock("@/hooks/useMyGroups", () => ({
  useMyGroups: () => ({
    data: {
      groups: [
        { group_id: "g1", name: "Rock Squad", invite_code: "ROCK1234", event_id: "ev1",
          created_by_user_id: "u1", last_active_at: "2026-07-01T00:00:00Z", archived_at: null,
          member_id: "m1", joined_at: "2026-07-01T00:00:00Z" },
        { group_id: "g2", name: "EDM Crew", invite_code: "EDM12345", event_id: "ev1",
          created_by_user_id: "u2", last_active_at: "2026-07-01T00:00:00Z", archived_at: null,
          member_id: "m2", joined_at: "2026-07-01T00:00:00Z" },
      ],
    },
  }),
}));
jest.mock("@/auth/AuthContext", () => ({
  useAuth: () => ({ signOut: mockSignOut, isLoading: false, isAuthenticated: true, signIn: jest.fn() }),
}));
jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Subject ─────────────────────────────────────────────────────────────────

import { AccountProfile } from "@/screens/profile/AccountProfile";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  mockSaveProfile.mockReset();
  mockLeaveGroup.mockReset();
  mockSignOut.mockReset();
  mockSaving = false;
  mockLeaving = false;
});

test("renders_display_name_input", () => {
  const { getByTestId } = render(<AccountProfile />, { wrapper });
  expect(getByTestId("display-name-input")).toBeTruthy();
});

test("save_btn_disabled_when_name_empty", () => {
  const { getByTestId } = render(<AccountProfile />, { wrapper });
  expect(getByTestId("save-btn").props.accessibilityState?.disabled).toBe(true);
});

test("save_btn_enabled_when_name_filled", () => {
  const { getByTestId } = render(<AccountProfile />, { wrapper });
  fireEvent.changeText(getByTestId("display-name-input"), "Jerome");
  expect(getByTestId("save-btn").props.accessibilityState?.disabled).toBeFalsy();
});

test("save_btn_calls_updateProfile_with_correct_payload", () => {
  const { getByTestId } = render(<AccountProfile />, { wrapper });
  fireEvent.changeText(getByTestId("display-name-input"), "Jerome");
  fireEvent.press(getByTestId("save-btn"));
  expect(mockSaveProfile).toHaveBeenCalledWith(
    expect.objectContaining({ display_name: "Jerome", avatar_color: expect.any(String) }),
    expect.anything()
  );
});

test("tap_swatch_updates_avatar_color", () => {
  const { getByTestId } = render(<AccountProfile />, { wrapper });
  // Tap a specific color swatch
  fireEvent.press(getByTestId("swatch-#ff2d9b"));
  // Now save and verify the color is in the payload
  fireEvent.changeText(getByTestId("display-name-input"), "Jerome");
  fireEvent.press(getByTestId("save-btn"));
  expect(mockSaveProfile).toHaveBeenCalledWith(
    expect.objectContaining({ avatar_color: "#ff2d9b" }),
    expect.anything()
  );
});

test("renders_group_list_with_leave_buttons", () => {
  const { getByTestId } = render(<AccountProfile />, { wrapper });
  expect(getByTestId("leave-btn-g1")).toBeTruthy();
  expect(getByTestId("leave-btn-g2")).toBeTruthy();
});

test("tap_leave_btn_shows_modal", () => {
  const { getByTestId, getByText } = render(<AccountProfile />, { wrapper });
  fireEvent.press(getByTestId("leave-btn-g1"));
  expect(getByText(/Leave group/)).toBeTruthy();
});

test("confirm_leave_calls_leaveGroup", () => {
  const { getByTestId } = render(<AccountProfile />, { wrapper });
  fireEvent.press(getByTestId("leave-btn-g1"));
  fireEvent.press(getByTestId("confirm-leave-btn"));
  expect(mockLeaveGroup).toHaveBeenCalledWith("ROCK1234", expect.objectContaining({ onSuccess: expect.any(Function) }));
});

test("cancel_leave_hides_modal", () => {
  const { getByTestId, queryByTestId } = render(<AccountProfile />, { wrapper });
  fireEvent.press(getByTestId("leave-btn-g1"));
  fireEvent.press(getByTestId("cancel-leave-btn"));
  expect(queryByTestId("confirm-leave-btn")).toBeNull();
});

test("sign_out_btn_calls_signOut", () => {
  const { getByTestId } = render(<AccountProfile />, { wrapper });
  fireEvent.press(getByTestId("sign-out-btn"));
  expect(mockSignOut).toHaveBeenCalled();
});
