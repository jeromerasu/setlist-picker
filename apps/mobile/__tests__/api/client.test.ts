import type { TokenPair } from "../../src/types/api";

// ---- mocks ----------------------------------------------------------------

const _store: Record<string, string> = {};

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn((key: string) => Promise.resolve(_store[key] ?? null)),
  setItemAsync: jest.fn((key: string, value: string) => {
    _store[key] = value;
    return Promise.resolve();
  }),
  deleteItemAsync: jest.fn((key: string) => {
    delete _store[key];
    return Promise.resolve();
  }),
}));

const _fetchMock = jest.fn<Promise<Response>, [RequestInfo | URL, RequestInit | undefined]>();
(global as typeof globalThis).fetch = _fetchMock as typeof fetch;

// ---- helpers ---------------------------------------------------------------

function _makePair(suffix = ""): TokenPair {
  return {
    access_token: `acc${suffix}`,
    refresh_token: `ref${suffix}`,
    token_type: "bearer",
    access_expires_at: "2099-01-01T00:00:00Z",
    refresh_expires_at: "2099-01-01T00:00:00Z",
  };
}

function _resp(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response;
}

// ---- tests ----------------------------------------------------------------

import { getTokens, setTokens } from "../../src/auth/token-store";
import { ApiError, UnauthenticatedError, fetchWithAuth } from "../../src/api/client";

beforeEach(() => {
  Object.keys(_store).forEach((k) => delete _store[k]);
  _fetchMock.mockReset();
});

describe("fetchWithAuth", () => {
  it("fetch_with_auth_attaches_bearer_token", async () => {
    await setTokens(_makePair());
    _fetchMock.mockResolvedValueOnce(_resp(200, { ok: true }));

    await fetchWithAuth("/api/test");

    const [, init] = _fetchMock.mock.calls[0];
    const headers = init?.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer acc");
  });

  it("fetch_with_auth_refreshes_on_401_then_retries_once", async () => {
    await setTokens(_makePair());
    const newPair = _makePair("_new");

    _fetchMock
      .mockResolvedValueOnce(_resp(401, {})) // original request
      .mockResolvedValueOnce(_resp(200, newPair)) // refresh
      .mockResolvedValueOnce(_resp(200, { data: "ok" })); // retry

    const result = await fetchWithAuth<{ data: string }>("/api/test");
    expect(result.data).toBe("ok");
    expect(_fetchMock).toHaveBeenCalledTimes(3);
    // Second call is the refresh endpoint
    expect((_fetchMock.mock.calls[1][0] as string).endsWith("/api/auth/refresh")).toBe(true);
  });

  it("fetch_with_auth_clears_tokens_on_refresh_failure", async () => {
    await setTokens(_makePair());

    _fetchMock
      .mockResolvedValueOnce(_resp(401, {})) // original 401
      .mockResolvedValueOnce(_resp(401, { error_code: "token_expired" })); // refresh fails

    await expect(fetchWithAuth("/api/test")).rejects.toBeInstanceOf(UnauthenticatedError);

    // getTokens is already imported at the top of this module
    const tokens = await getTokens();
    expect(tokens).toBeNull();
  });

  it("fetch_with_auth_parses_error_response", async () => {
    await setTokens(_makePair());
    _fetchMock.mockResolvedValueOnce(
      _resp(400, { error_code: "validation_error", message: "Bad input", request_id: null }),
    );

    const err = await fetchWithAuth("/api/test").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).error_code).toBe("validation_error");
    expect((err as ApiError).statusCode).toBe(400);
  });
});
