import React from "react";
import { render, fireEvent, waitFor, act } from "@testing-library/react-native";

// ─── Navigation mock ─────────────────────────────────────────────────────────

const mockGoBack = jest.fn();
const mockNavigate = jest.fn();

jest.mock("@react-navigation/native", () => {
  const RN = require("react-native");
  return {
    useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack }),
    NavigationContainer: ({ children }: { children: React.ReactNode }) =>
      RN.createElement(RN.View, null, children),
  };
});

jest.mock("@react-navigation/native-stack", () => ({
  createNativeStackNavigator: () => ({
    Navigator: ({ children }: { children: React.ReactNode }) => {
      const { View } = require("react-native");
      return require("react").createElement(View, null, children);
    },
    Screen: () => null,
  }),
}));

// ─── Auth mock ───────────────────────────────────────────────────────────────

const mockSignIn = jest.fn();
const mockLogin = jest.fn();

jest.mock("@/auth/AuthContext", () => ({
  useAuth: () => ({ signIn: mockSignIn, isAuthenticated: false, isLoading: false }),
}));

jest.mock("@/auth/useLocalAuth", () => ({
  useLocalAuth: () => ({
    isLoading: false,
    error: null,
    login: mockLogin,
    signup: jest.fn(async () => null),
  }),
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Subject ─────────────────────────────────────────────────────────────────

import { LocalLogin } from "@/screens/auth/LocalLogin";

beforeEach(() => {
  mockSignIn.mockReset();
  mockLogin.mockReset();
  mockNavigate.mockReset();
  mockGoBack.mockReset();
});

test("local_login_submit_disabled_when_fields_empty", () => {
  const { getByTestId } = render(<LocalLogin />);
  const btn = getByTestId("submit-btn");
  expect(btn.props.accessibilityState?.disabled ?? btn.props.disabled).toBeTruthy();
});

test("local_login_calls_login_and_signIn_on_success", async () => {
  mockLogin.mockResolvedValueOnce({ access_token: "a", refresh_token: "r", token_type: "bearer" });

  const { getByTestId } = render(<LocalLogin />);
  fireEvent.changeText(getByTestId("email-input"), "jerome@example.com");
  fireEvent.changeText(getByTestId("password-input"), "hunter22");

  await act(async () => { fireEvent.press(getByTestId("submit-btn")); });

  await waitFor(() => {
    expect(mockLogin).toHaveBeenCalledWith("jerome@example.com", "hunter22");
    expect(mockSignIn).toHaveBeenCalledWith({ access_token: "a", refresh_token: "r", token_type: "bearer" });
  });
});

test("local_login_back_chip_calls_goBack", () => {
  const { getByLabelText } = render(<LocalLogin />);
  fireEvent.press(getByLabelText("Go back"));
  expect(mockGoBack).toHaveBeenCalled();
});
