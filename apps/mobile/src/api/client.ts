import { clearTokens, getTokens, setTokens } from "@/auth/token-store";
import type { ErrorResponse, TokenPair } from "@/types/api";

export const BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "https://setlist-picker-dev.onrender.com";

export class ApiError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly error_code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class UnauthenticatedError extends Error {
  constructor() {
    super("Unauthenticated — no valid session");
    this.name = "UnauthenticatedError";
  }
}

async function _doFetch(
  path: string,
  accessToken: string | null,
  init?: RequestInit,
): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  return fetch(`${BASE_URL}${path}`, { ...init, headers });
}

async function _parseError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as ErrorResponse;
    return new ApiError(
      res.status,
      body.error_code ?? "unknown_error",
      body.message ?? `HTTP ${res.status}`,
    );
  } catch {
    return new ApiError(res.status, "unknown_error", `HTTP ${res.status}`);
  }
}

export async function fetchWithAuth<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const pair = await getTokens();
  const accessToken = pair?.access_token ?? null;

  const res = await _doFetch(path, accessToken, init);

  if (res.status === 401 && pair?.refresh_token) {
    // Attempt a token refresh, then retry once
    const refreshRes = await _doFetch("/api/auth/refresh", null, {
      method: "POST",
      body: JSON.stringify({ refresh_token: pair.refresh_token }),
    });

    if (refreshRes.ok) {
      const newPair = (await refreshRes.json()) as TokenPair;
      await setTokens(newPair);
      const retryRes = await _doFetch(path, newPair.access_token, init);
      if (retryRes.ok) {
        return retryRes.json() as Promise<T>;
      }
      throw await _parseError(retryRes);
    }

    // Refresh failed — clear tokens and throw
    await clearTokens();
    throw new UnauthenticatedError();
  }

  if (res.status === 401) {
    await clearTokens();
    throw new UnauthenticatedError();
  }

  if (!res.ok) {
    throw await _parseError(res);
  }

  return res.json() as Promise<T>;
}
