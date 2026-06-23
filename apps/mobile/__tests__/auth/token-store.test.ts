import type { TokenPair } from "../../src/types/api";

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

import { clearTokens, getTokens, setTokens } from "../../src/auth/token-store";

const _PAIR: TokenPair = {
  access_token: "acc",
  refresh_token: "ref",
  token_type: "bearer",
  access_expires_at: "2099-01-01T00:00:00Z",
  refresh_expires_at: "2099-01-01T00:00:00Z",
};

beforeEach(() => {
  Object.keys(_store).forEach((k) => delete _store[k]);
});

describe("token-store", () => {
  it("set_then_get_round_trips", async () => {
    await setTokens(_PAIR);
    const result = await getTokens();
    expect(result).toEqual(_PAIR);
  });

  it("clear_removes_both_keys", async () => {
    await setTokens(_PAIR);
    await clearTokens();
    const result = await getTokens();
    expect(result).toBeNull();
  });
});
