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
import { useCreateGroup } from "@/hooks/useCreateGroup";

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

test("posts_to_groups_endpoint_with_name_and_event_id", async () => {
  (fetchWithAuth as jest.Mock).mockResolvedValueOnce({
    group_id: "g1",
    name: "Ravefam",
    invite_code: "ABCD1234",
    event_id: "e1",
    created_by_user_id: "u1",
    created_at: "2026-06-01T00:00:00Z",
    member_id: "m1",
  });

  const { result } = renderHook(() => useCreateGroup(), { wrapper: makeWrapper() });

  await act(async () => {
    result.current.mutate({ name: "Ravefam", event_id: "e1" });
    await new Promise((r) => setTimeout(r, 0));
  });

  expect(fetchWithAuth).toHaveBeenCalledWith(
    "/api/groups",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ name: "Ravefam", event_id: "e1" }),
    })
  );
});
