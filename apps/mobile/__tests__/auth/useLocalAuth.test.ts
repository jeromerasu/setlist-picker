import { act, renderHook } from "@testing-library/react-native";
import { useLocalAuth } from "@/auth/useLocalAuth";

const _fetchMock = jest.fn();
beforeEach(() => {
  _fetchMock.mockReset();
  (global as typeof globalThis).fetch = _fetchMock;
});

test("login_returns_token_pair_on_200", async () => {
  _fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ access_token: "a", refresh_token: "r", token_type: "bearer" }),
  });

  const { result } = renderHook(() => useLocalAuth());
  let pair: Awaited<ReturnType<typeof result.current.login>>;

  await act(async () => {
    pair = await result.current.login("jerome", "hunter2");
  });

  expect(pair!).toEqual({ access_token: "a", refresh_token: "r", token_type: "bearer" });
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
    pair = await result.current.login("jerome", "wrong");
  });

  expect(pair!).toBeNull();
  expect(result.current.error).toBe("Invalid credentials");
});

test("login_sets_network_error_on_throw", async () => {
  _fetchMock.mockRejectedValueOnce(new Error("network"));

  const { result } = renderHook(() => useLocalAuth());
  await act(async () => { await result.current.login("u", "p"); });
  expect(result.current.error).toBe("Network error — check your connection");
});

test("signup_returns_token_pair_on_200", async () => {
  _fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ access_token: "a", refresh_token: "r", token_type: "bearer" }),
  });

  const { result } = renderHook(() => useLocalAuth());
  let pair: Awaited<ReturnType<typeof result.current.signup>>;

  await act(async () => {
    pair = await result.current.signup("jerome", "secret123", "Jerome");
  });

  expect(pair!).toEqual({ access_token: "a", refresh_token: "r", token_type: "bearer" });
});

test("signup_sends_snake_case_body", async () => {
  _fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ access_token: "a", refresh_token: "r", token_type: "bearer" }),
  });

  const { result } = renderHook(() => useLocalAuth());
  await act(async () => { await result.current.signup("jerome", "secret123", "Jerome R"); });

  const body = JSON.parse(_fetchMock.mock.calls[0][1].body as string);
  expect(body).toHaveProperty("display_name", "Jerome R");
  expect(body).not.toHaveProperty("displayName");
});
