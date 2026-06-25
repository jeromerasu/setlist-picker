import React from "react";
import { render } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── Mocks ───────────────────────────────────────────────────────────────────

const mockUseIsMutating = jest.fn((_opts?: unknown) => 0);
const mockUseQueryClient = jest.fn();

jest.mock("@tanstack/react-query", () => ({
  ...jest.requireActual("@tanstack/react-query"),
  useIsMutating: (opts?: unknown) => mockUseIsMutating(opts),
  useQueryClient: () => mockUseQueryClient(),
}));

jest.mock("@/lib/offlinePickQueue", () => ({
  peekPickQueue: jest.fn(async () => []),
  removePickOp: jest.fn(async () => {}),
}));

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

// NetInfo and AsyncStorage resolved via moduleNameMapper

import { useNetInfo } from "@react-native-community/netinfo";
import { OfflineBadge } from "@/components/OfflineBadge";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetInfo as jest.Mock).mockReturnValue({ isConnected: true, isInternetReachable: true });
  mockUseIsMutating.mockReturnValue(0);
  mockUseQueryClient.mockReturnValue({ invalidateQueries: jest.fn(async () => {}) });
});

// ─── Tests ───────────────────────────────────────────────────────────────────

test("renders_when_offline", () => {
  (useNetInfo as jest.Mock).mockReturnValue({ isConnected: false, isInternetReachable: false });
  const { getByTestId, getByText } = render(
    <OfflineBadge invite_code="TESTCODE" />, { wrapper },
  );
  expect(getByTestId("offline-badge")).toBeTruthy();
  expect(getByText("Offline — picks queued")).toBeTruthy();
});

test("renders_when_mutations_pending", () => {
  mockUseIsMutating.mockReturnValue(2);
  const { getByTestId, getByText } = render(
    <OfflineBadge invite_code="TESTCODE" />, { wrapper },
  );
  expect(getByTestId("offline-badge")).toBeTruthy();
  expect(getByText("Syncing 2 picks…")).toBeTruthy();
});

test("hides_when_online_and_idle", () => {
  (useNetInfo as jest.Mock).mockReturnValue({ isConnected: true, isInternetReachable: true });
  mockUseIsMutating.mockReturnValue(0);
  const { queryByTestId } = render(
    <OfflineBadge invite_code="TESTCODE" />, { wrapper },
  );
  expect(queryByTestId("offline-badge")).toBeNull();
});
