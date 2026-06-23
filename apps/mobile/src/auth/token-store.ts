import * as SecureStore from "expo-secure-store";
import type { TokenPair } from "@/types/api";

const ACCESS_KEY = "sp_access_token";
const REFRESH_KEY = "sp_refresh_token";
const PAIR_KEY = "sp_token_pair";

export async function getTokens(): Promise<TokenPair | null> {
  const raw = await SecureStore.getItemAsync(PAIR_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as TokenPair;
  } catch {
    return null;
  }
}

export async function setTokens(pair: TokenPair): Promise<void> {
  await SecureStore.setItemAsync(PAIR_KEY, JSON.stringify(pair));
}

export async function clearTokens(): Promise<void> {
  await SecureStore.deleteItemAsync(PAIR_KEY);
  // Delete legacy individual keys in case they were written by an older version
  await SecureStore.deleteItemAsync(ACCESS_KEY).catch(() => undefined);
  await SecureStore.deleteItemAsync(REFRESH_KEY).catch(() => undefined);
}
