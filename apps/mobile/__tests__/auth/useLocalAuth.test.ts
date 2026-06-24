import { act, renderHook } from "@testing-library/react-native";
import { useLocalAuth } from "@/auth/useLocalAuth";

const _TOKENS = { access_token: "a", refresh_token: "r", token_type: "bearer" as const, access_expires_at: "2099-01-01T00:00:00Z", refresh_expires_at: "2099-01-01T00:00:00Z" };
const _AUTH_RESPONSE = { tokens: _TOKENS, user: { id: "u1", auth_provider: "local", email: "j@x.com", display_name: null, avatar_color: "#000", created_at: "2026-01-01T00:00:00Z", last_login_at: null } };

const _fetchMock = jest.fn();
beforeEach(() => {
  _fetchMock.mockReset();
  (global as typeof globalThis).fetch = _fetchMock;
});

test("login_returns_token_pair_on_200", async () => {
  _fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => _AUTH_RESPONSE,
  });

  const { result } = renderHook(() => useLocalAuth());
  let pair: Awaited<ReturnType<typeof result.current.login>>;

  await act(async () => {
    pair = await result.current.login("jerome@example.com", "hunter2");
  });

  expect(pair!).toEqual(_TOKENS);
  expect(result.current.error).toBeNull();
});

test("login_sets_error_on_non_ok", async () => {
  _fetchMock.mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: "Invalid credentials" }),
  });

  const { result } = renderHook(() => useLocalAuth());
  let pair: Awaited<ReturnType<typeof result.current.login>>;

  await act(async () => {
    pair = await result.current.login("jerome@example.com", "wrong");
  });

  expect(pair!).toBeNull();
  expect(result.current.error).toBe("Invalid credentials");
});

test("login_sets_network_error_on_throw", async () => {
  _fetchMock.mockRejectedValueOnce(new Error("network"));

  const { result } = renderHook(() => useLocalAuth());
  await act(async () => { await result.current.login("u@x.com", "p"); });
  expect(result.current.error).toBe("Network error — check your connection");
});

test("signup_returns_token_pair_on_200", async () => {
  _fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => _AUTH_RESPONSE,
  });

  const { result } = renderHook(() => useLocalAuth());
  let pair: Awaited<ReturnType<typeof result.current.signup>>;

  await act(async () => {
    pair = await result.current.signup("jerome@example.com", "secret123", "Jerome");
  });

  expect(pair!).toEqual(_TOKENS);
});

test("signup_sends_snake_case_body", async () => {
  _fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => _AUTH_RESPONSE,
  });

  const { result } = renderHook(() => useLocalAuth());
  await act(async () => { await result.current.signup("jerome@example.com", "secret123", "Jerome R"); });

  const body = JSON.parse(_fetchMock.mock.calls[0][1].body as string);
  expect(body).toHaveProperty("display_name", "Jerome R");
  expect(body).not.toHaveProperty("displayName");
});
