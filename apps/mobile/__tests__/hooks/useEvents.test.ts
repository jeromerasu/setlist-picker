import { renderHook, waitFor, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

jest.mock("@/api/client", () => ({
  fetchWithAuth: jest.fn(),
  ApiError: class ApiError extends Error {},
  UnauthenticatedError: class UnauthenticatedError extends Error {},
}));

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

import { fetchWithAuth } from "@/api/client";
import { useEvents } from "@/hooks/useEvents";

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  jest.useFakeTimers();
  (fetchWithAuth as jest.Mock).mockResolvedValue({ events: [] });
});

afterEach(() => {
  jest.useRealTimers();
});

test("query_param_passed_to_be", async () => {
  (fetchWithAuth as jest.Mock).mockResolvedValue({ events: [] });
  const { result } = renderHook(() => useEvents("edc"), { wrapper: makeWrapper() });
  act(() => { jest.advanceTimersByTime(300); });
  await waitFor(() => expect(result.current.isFetched).toBe(true));
  expect((fetchWithAuth as jest.Mock).mock.calls[0][0]).toContain("q=edc");
});

test("debounces_on_typing", async () => {
  (fetchWithAuth as jest.Mock).mockResolvedValue({ events: [] });
  const { rerender, result } = renderHook<ReturnType<typeof useEvents>, { q: string }>(
    ({ q }: { q: string }) => useEvents(q),
    { wrapper: makeWrapper(), initialProps: { q: "e" } }
  );

  // Quickly update before debounce fires
  act(() => { rerender({ q: "ed" }); });
  act(() => { rerender({ q: "edc" }); });
  const callsBefore = (fetchWithAuth as jest.Mock).mock.calls.length;

  act(() => { jest.advanceTimersByTime(350); });
  await waitFor(() => expect(result.current.isFetched).toBe(true));

  const callsAfter = (fetchWithAuth as jest.Mock).mock.calls.length;
  expect(callsAfter - callsBefore).toBeLessThanOrEqual(2);
});
