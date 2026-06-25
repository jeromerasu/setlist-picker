/**
 * SETLIST-OFFLINE-PICK-QUEUE: verifies that network errors preserve optimistic
 * state and queue the op in AsyncStorage, while server errors roll back.
 */
import { renderHook, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
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

// AsyncStorage and NetInfo are auto-resolved from moduleNameMapper.

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
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  return { qc, Wrapper };
}

beforeEach(() => {
  jest.clearAllMocks();
  // Reset the in-memory AsyncStorage mock store
  (AsyncStorage as unknown as { _store: Record<string, string> })._store &&
    Object.keys((AsyncStorage as unknown as { _store: Record<string, string> })._store)
      .forEach((k) => { delete (AsyncStorage as unknown as { _store: Record<string, string> })._store[k]; });
});

test("network_error_preserves_optimistic_state_and_queues_op", async () => {
  // Simulate a network error (TypeError — no response from server)
  (fetchWithAuth as jest.Mock).mockRejectedValueOnce(
    new TypeError("Network request failed"),
  );

  const { qc, Wrapper } = makeWrapper();
  qc.setQueryData(["group", "TESTCODE"], { ...SEED_GROUP, picks: [] });

  const { result } = renderHook(() => usePickToggle(), { wrapper: Wrapper });

  await act(async () => {
    result.current.mutate({ invite_code: "TESTCODE", set_id: "s2", is_picked: false, member_id: "m1" });
    await new Promise((r) => setTimeout(r, 50));
  });

  // Optimistic state must still be in cache (no rollback)
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

test("server_error_rolls_back_optimistic_state_and_removes_from_queue", async () => {
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

  // Optimistic state must be rolled back
  const cached = qc.getQueryData<GroupStateResponse>(["group", "TESTCODE"]);
  expect(cached?.picks).not.toContainEqual(expect.objectContaining({ set_id: "s3" }));

  // Queue entry must have been removed
  const raw = await AsyncStorage.getItem("@picks_offline_queue_v1");
  const queue = raw ? (JSON.parse(raw) as Array<{ set_id: string }>) : [];
  expect(queue).not.toContainEqual(expect.objectContaining({ set_id: "s3" }));
});

test("successful_pick_removes_op_from_queue", async () => {
  (fetchWithAuth as jest.Mock).mockResolvedValueOnce({
    group_id: "g1",
    set_id: "s4",
    member_id: "m1",
    state: "active",
    state_clock_ms: 1000,
  });

  const { qc, Wrapper } = makeWrapper();
  qc.setQueryData(["group", "TESTCODE"], { ...SEED_GROUP, picks: [] });

  const { result } = renderHook(() => usePickToggle(), { wrapper: Wrapper });

  await act(async () => {
    result.current.mutate({ invite_code: "TESTCODE", set_id: "s4", is_picked: false, member_id: "m1" });
    await new Promise((r) => setTimeout(r, 50));
  });

  // Queue must be empty after success
  const raw = await AsyncStorage.getItem("@picks_offline_queue_v1");
  const queue = raw ? (JSON.parse(raw) as Array<{ set_id: string }>) : [];
  expect(queue).not.toContainEqual(expect.objectContaining({ set_id: "s4" }));
});
