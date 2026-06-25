import { QueryClient, onlineManager } from "@tanstack/react-query";
import NetInfo from "@react-native-community/netinfo";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import AsyncStorage from "@react-native-async-storage/async-storage";

// Wire React Native's NetInfo into React Query's online manager so that
// paused mutations auto-resume when the device reconnects (RN's navigator.onLine
// is unreliable; NetInfo is the correct signal).
onlineManager.setEventListener((setOnline) =>
  NetInfo.addEventListener((state) => {
    setOnline(!!state.isConnected && state.isInternetReachable !== false);
  }),
);

// Exported for App.tsx — used by PersistQueryClientProvider
export const asyncStoragePersister = createAsyncStoragePersister({
  storage: AsyncStorage,
});

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
      networkMode: "offlineFirst",
    },
    mutations: {
      networkMode: "offlineFirst",
    },
  },
});
