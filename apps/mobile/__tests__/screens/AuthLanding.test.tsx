import React from "react";
import { render, fireEvent } from "@testing-library/react-native";

// ─── Navigation mock ─────────────────────────────────────────────────────────

const mockNavigate = jest.fn();

jest.mock("@react-navigation/native", () => {
  const RN = require("react-native");
  return {
    useNavigation: () => ({ navigate: mockNavigate, goBack: jest.fn() }),
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

jest.mock("@/auth/AuthContext", () => ({
  useAuth: () => ({ signIn: mockSignIn, isAuthenticated: false, isLoading: false }),
}));

jest.mock("@/auth/useAppleSignIn", () => ({
  useAppleSignIn: () => ({
    isLoading: false,
    error: null,
    signInWithApple: jest.fn(async () => null),
  }),
}));

jest.mock("@/auth/useGoogleSignIn", () => ({
  useGoogleSignIn: () => ({
    isLoading: false,
    error: null,
    signInWithGoogle: jest.fn(async () => null),
  }),
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// ─── Subject ─────────────────────────────────────────────────────────────────

import { AuthLanding } from "@/screens/auth/AuthLanding";

beforeEach(() => { mockNavigate.mockReset(); mockSignIn.mockReset(); });

test("auth_landing_renders_ctas", () => {
  const { getByTestId } = render(<AuthLanding />);
  expect(getByTestId("apple-btn")).toBeTruthy();
  expect(getByTestId("google-btn")).toBeTruthy();
  expect(getByTestId("email-btn")).toBeTruthy();
  expect(getByTestId("signup-link")).toBeTruthy();
});

test("auth_landing_email_btn_navigates_to_local_login", () => {
  const { getByTestId } = render(<AuthLanding />);
  fireEvent.press(getByTestId("email-btn"));
  expect(mockNavigate).toHaveBeenCalledWith("LocalLogin");
});

test("auth_landing_signup_link_navigates_to_local_signup", () => {
  const { getByTestId } = render(<AuthLanding />);
  fireEvent(getByTestId("signup-link"), "press");
  expect(mockNavigate).toHaveBeenCalledWith("LocalSignup");
});
