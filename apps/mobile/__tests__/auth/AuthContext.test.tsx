import React from "react";
import { Text } from "react-native";
import { render, act, waitFor } from "@testing-library/react-native";

// ─── Mocks ──────────────────────────────────────────────────────────────────

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

import * as SecureStore from "expo-secure-store";

// ─── Subject ─────────────────────────────────────────────────────────────────

import { AuthProvider, useAuth } from "@/auth/AuthContext";

const PAIR = {
  access_token: "tok",
  refresh_token: "ref",
  token_type: "bearer" as const,
  access_expires_at: "2099-01-01T00:00:00Z",
  refresh_expires_at: "2099-06-01T00:00:00Z",
};

function Consumer() {
  const { isLoading, isAuthenticated } = useAuth();
  if (isLoading) return <Text testID="loading">loading</Text>;
  return <Text testID="status">{isAuthenticated ? "authed" : "anon"}</Text>;
}

function SignInConsumer() {
  const { signIn, isAuthenticated } = useAuth();
  return (
    <>
      <Text testID="status">{isAuthenticated ? "authed" : "anon"}</Text>
      <Text
        testID="sign-in-btn"
        onPress={() =>
          void signIn(PAIR)
        }
      >
        sign in
      </Text>
    </>
  );
}

function SignOutConsumer() {
  const { signIn, signOut, isAuthenticated } = useAuth();
  return (
    <>
      <Text testID="status">{isAuthenticated ? "authed" : "anon"}</Text>
      <Text
        testID="sign-in-btn"
        onPress={() =>
          void signIn(PAIR)
        }
      >
        sign in
      </Text>
      <Text testID="sign-out-btn" onPress={() => void signOut()}>
        sign out
      </Text>
    </>
  );
}

// ─── Tests ───────────────────────────────────────────────────────────────────

let _stored: string | null = null;

beforeEach(() => {
  _stored = null;
  (SecureStore.getItemAsync as jest.Mock).mockImplementation(async () => _stored);
  (SecureStore.setItemAsync as jest.Mock).mockImplementation(async (_key: string, value: string) => {
    _stored = value;
  });
  (SecureStore.deleteItemAsync as jest.Mock).mockImplementation(async () => {
    _stored = null;
  });
});

test("auth_context_starts_loading_then_anon_when_no_tokens", async () => {
  const { getByTestId } = render(
    <AuthProvider>
      <Consumer />
    </AuthProvider>
  );
  expect(getByTestId("loading")).toBeTruthy();
  await waitFor(() => expect(getByTestId("status").props.children).toBe("anon"));
});

test("auth_context_is_authenticated_when_stored_tokens_exist", async () => {
  _stored = JSON.stringify({ ...PAIR, access_token: "stored" });
  const { getByTestId } = render(
    <AuthProvider>
      <Consumer />
    </AuthProvider>
  );
  await waitFor(() => expect(getByTestId("status").props.children).toBe("authed"));
});

test("sign_in_sets_authenticated", async () => {
  const { getByTestId } = render(
    <AuthProvider>
      <SignInConsumer />
    </AuthProvider>
  );
  await waitFor(() => expect(getByTestId("status").props.children).toBe("anon"));
  await act(async () => { getByTestId("sign-in-btn").props.onPress(); });
  await waitFor(() => expect(getByTestId("status").props.children).toBe("authed"));
});

test("sign_out_clears_authenticated", async () => {
  _stored = JSON.stringify(PAIR);
  const { getByTestId } = render(
    <AuthProvider>
      <SignOutConsumer />
    </AuthProvider>
  );
  await waitFor(() => expect(getByTestId("status").props.children).toBe("authed"));
  await act(async () => { getByTestId("sign-out-btn").props.onPress(); });
  await waitFor(() => expect(getByTestId("status").props.children).toBe("anon"));
});

test("useAuth_throws_outside_provider", () => {
  const spy = jest.spyOn(console, "error").mockImplementation(() => undefined);
  expect(() => render(<Consumer />)).toThrow("useAuth must be used inside AuthProvider");
  spy.mockRestore();
});
