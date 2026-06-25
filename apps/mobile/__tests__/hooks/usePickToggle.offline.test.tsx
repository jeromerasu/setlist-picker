import { renderHook, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider, onlineManager } from "@tanstack/react-query";
import React from "react";

jest.mock("@/api/client", () => ({
  fetchWithAuth: jest.fn(),
  ApiError: class ApiError extends Error {
    statusCode: number;
    error_code: string;
    constructor(message: string, statusCode: number, error_code: string) {
      super(message);
      this.name = "ApiError";
      this.statusCode = statusCode;
      this.error_code = error_code;
    }
  },
  UnauthenticatedError: class UnauthenticatedError extends Error {
    constructor() { super("unauth"); this.name = "UnauthenticatedError"; }
  },
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

// AsyncStorage resolved by moduleNameMapper → src/__mocks__/asyncStorage.ts

import { fetchWithAuth } from "@/api/client";
import { usePickToggle } from "@/hooks/usePickToggle";
import AsyncStorage from "@react-native-async-storage/async-storage";
import type { GroupStateResponse } from "@/types/api";

const SEED_GROUP: GroupStateResponse = {
  group_id: "g1",
  invite_code: "TESTCODE",
  name: "Ravefam",
  event: {
    event_id: "e1",
    name: "Tomorrowland",
    start_date: "2026-07-24",
    end_date: "2026-07-26",
    location: "Boom",
    timezone: "Europe/Brussels",
  },
  members: [{
    member_id: "m1",
    user_id: "u1",
    group_id: "g1",
    display_name: "Jerome",
    display_name_override: null,
    avatar_color: "#a78bfa",
    joined_at: "2026-06-01T00:00:00Z",
  }],
  picks: [],
  archived_at: null,
  last_active_at: "2026-06-24T00:00:00Z",
};

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false, networkMode: "offlineFirst" as const },
    },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  return { qc, Wrapper };
}

function clearAsyncStore() {
  const store = (AsyncStorage as unknown as { _store: Record<string, string> })._store;
  if (store) Object.keys(store).forEach((k) => { delete store[k]; });
}

beforeEach(() => {
  jest.clearAllMocks();
  clearAsyncStore();
  onlineManager.setOnline(true);
});

afterEach(() => {
  onlineManager.setOnline(true);
});

// Verify that when a network error occurs the op is durably queued
// and the optimistic state is preserved so it shows on reconnect.
test("queues_when_offline_and_drains_on_reconnect", async () => {
  (fetchWithAuth as jest.Mock).mockRejectedValueOnce(new TypeError("Network request failed"));

  const { qc, Wrapper } = makeWrapper();
  qc.setQueryData(["group", "TESTCODE"], { ...SEED_GROUP, picks: [] });

  const { result } = renderHook(() => usePickToggle(), { wrapper: Wrapper });

  await act(async () => {
    result.current.mutate({ invite_code: "TESTCODE", set_id: "s2", is_picked: false, member_id: "m1" });
    await new Promise((r) => setTimeout(r, 50));
  });

  // Network error → optimistic state is preserved (no rollback), ready to sync on reconnect
  const cached = qc.getQueryData<GroupStateResponse>(["group", "TESTCODE"]);
  expect(cached?.picks).toContainEqual(expect.objectContaining({ set_id: "s2", member_id: "m1" }));

  // Op is durably queued in AsyncStorage for recovery after app kill
  const raw = await AsyncStorage.getItem("@picks_offline_queue_v1");
  expect(raw).not.toBeNull();
  const queue = JSON.parse(raw!) as Array<{ set_id: string }>;
  expect(queue).toContainEqual(expect.objectContaining({ set_id: "s2", invite_code: "TESTCODE" }));
});

test("preserves_optimistic_state_on_network_error", async () => {
  (fetchWithAuth as jest.Mock).mockRejectedValueOnce(new TypeError("Network request failed"));

  const { qc, Wrapper } = makeWrapper();
  qc.setQueryData(["group", "TESTCODE"], { ...SEED_GROUP, picks: [] });

  const { result } = renderHook(() => usePickToggle(), { wrapper: Wrapper });

  await act(async () => {
    result.current.mutate({ invite_code: "TESTCODE", set_id: "s2", is_picked: false, member_id: "m1" });
    await new Promise((r) => setTimeout(r, 50));
  });

  // Optimistic state must remain (no rollback on network error)
  const cached = qc.getQueryData<GroupStateResponse>(["group", "TESTCODE"]);
  expect(cached?.picks).toContainEqual(
    expect.objectContaining({ set_id: "s2", member_id: "m1", state: "active" }),
  );

  // Op must be in the AsyncStorage queue
  const raw = await AsyncStorage.getItem("@picks_offline_queue_v1");
  expect(raw).not.toBeNull();
  const queue = JSON.parse(raw!) as Array<{ set_id: string }>;
  expect(queue).toContainEqual(expect.objectContaining({ set_id: "s2", invite_code: "TESTCODE" }));
});

test("rolls_back_optimistic_state_on_server_error", async () => {
  const { ApiError } = jest.requireMock("@/api/client") as {
    ApiError: new (msg: string, code: number, ec: string) => Error;
  };
  (fetchWithAuth as jest.Mock).mockRejectedValueOnce(
    new ApiError("Conflict", 409, "pick_conflict"),
  );

  const { qc, Wrapper } = makeWrapper();
  qc.setQueryData(["group", "TESTCODE"], { ...SEED_GROUP, picks: [] });

  const { result } = renderHook(() => usePickToggle(), { wrapper: Wrapper });

  await act(async () => {
    result.current.mutate({ invite_code: "TESTCODE", set_id: "s3", is_picked: false, member_id: "m1" });
    await new Promise((r) => setTimeout(r, 50));
  });

  // Optimistic state must be rolled back to pre-mutate snapshot
  const cached = qc.getQueryData<GroupStateResponse>(["group", "TESTCODE"]);
  expect(cached?.picks).not.toContainEqual(expect.objectContaining({ set_id: "s3" }));

  // Queue entry removed on server error
  const raw = await AsyncStorage.getItem("@picks_offline_queue_v1");
  const queue = raw ? (JSON.parse(raw) as Array<{ set_id: string }>) : [];
  expect(queue).not.toContainEqual(expect.objectContaining({ set_id: "s3" }));
});

test("successful_pick_removes_op_from_queue", async () => {
  (fetchWithAuth as jest.Mock).mockResolvedValueOnce({
    group_id: "g1", set_id: "s4", member_id: "m1", state: "active", state_clock_ms: 1000,
  });

  const { qc, Wrapper } = makeWrapper();
  qc.setQueryData(["group", "TESTCODE"], { ...SEED_GROUP, picks: [] });

  const { result } = renderHook(() => usePickToggle(), { wrapper: Wrapper });

  await act(async () => {
    result.current.mutate({ invite_code: "TESTCODE", set_id: "s4", is_picked: false, member_id: "m1" });
    await new Promise((r) => setTimeout(r, 50));
  });

  const raw = await AsyncStorage.getItem("@picks_offline_queue_v1");
  const queue = raw ? (JSON.parse(raw) as Array<{ set_id: string }>) : [];
  expect(queue).not.toContainEqual(expect.objectContaining({ set_id: "s4" }));
});
