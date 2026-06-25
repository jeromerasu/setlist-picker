/**
 * FIX-PICK-TOGGLE-INSTANT-VISUAL: verifies that onMutate patches the cache
 * synchronously for both add and remove so the visual updates in the same frame.
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
      this.statusCode = statusCode;
      this.error_code = error_code;
    }
  },
  UnauthenticatedError: class UnauthenticatedError extends Error {},
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

import { fetchWithAuth } from "@/api/client";
import { usePickToggle } from "@/hooks/usePickToggle";
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

test("add_pick_immediately_patches_cache_with_new_entry", async () => {
  (fetchWithAuth as jest.Mock).mockReturnValue(new Promise(() => {})); // never resolves — keep in-flight

  const { qc, Wrapper } = makeWrapper();
  qc.setQueryData(["group", "TESTCODE"], { ...SEED_GROUP, picks: [] });

  const { result } = renderHook(() => usePickToggle(), { wrapper: Wrapper });

  act(() => {
    result.current.mutate({ invite_code: "TESTCODE", set_id: "s2", is_picked: false, member_id: "m1" });
  });
  await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

  const cached = qc.getQueryData<GroupStateResponse>(["group", "TESTCODE"]);
  expect(cached?.picks).toContainEqual(
    expect.objectContaining({ set_id: "s2", member_id: "m1", state: "active" }),
  );
});

test("remove_pick_immediately_removes_entry_from_cache", async () => {
  (fetchWithAuth as jest.Mock).mockReturnValue(new Promise(() => {}));

  const { qc, Wrapper } = makeWrapper();
  qc.setQueryData(["group", "TESTCODE"], {
    ...SEED_GROUP,
    picks: [{ member_id: "m1", set_id: "s1", state: "active", state_clock_ms: 1000 }],
  });

  const { result } = renderHook(() => usePickToggle(), { wrapper: Wrapper });

  act(() => {
    result.current.mutate({ invite_code: "TESTCODE", set_id: "s1", is_picked: true, member_id: "m1" });
  });
  await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

  const cached = qc.getQueryData<GroupStateResponse>(["group", "TESTCODE"]);
  expect(cached?.picks).not.toContainEqual(expect.objectContaining({ set_id: "s1" }));
});

test("add_pick_skips_cache_patch_when_member_id_empty", async () => {
  (fetchWithAuth as jest.Mock).mockReturnValue(new Promise(() => {}));

  const { qc, Wrapper } = makeWrapper();
  qc.setQueryData(["group", "TESTCODE"], { ...SEED_GROUP, picks: [] });

  const { result } = renderHook(() => usePickToggle(), { wrapper: Wrapper });

  act(() => {
    result.current.mutate({ invite_code: "TESTCODE", set_id: "s2", is_picked: false, member_id: "" });
  });
  await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

  const cached = qc.getQueryData<GroupStateResponse>(["group", "TESTCODE"]);
  // Cache unchanged — no optimistic patch without a valid member_id
  expect(cached?.picks).toHaveLength(0);
});
