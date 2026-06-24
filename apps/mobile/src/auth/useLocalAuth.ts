import { useState } from "react";
import type { AuthResponse, TokenPair } from "@/types/api";

import { BASE_URL as API_BASE } from "../api/client";

interface LocalAuthResult {
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<TokenPair | null>;
  signup: (email: string, password: string, display_name: string) => Promise<TokenPair | null>;
}

export function useLocalAuth(): LocalAuthResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = async (email: string, password: string): Promise<TokenPair | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = (await res.json()) as { detail?: string };
        setError(body.detail ?? "Login failed");
        return null;
      }
      return ((await res.json()) as AuthResponse).tokens;
    } catch {
      setError("Network error — check your connection");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (
    email: string,
    password: string,
    display_name: string
  ): Promise<TokenPair | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, display_name }),
      });
      if (!res.ok) {
        const body = (await res.json()) as { detail?: string };
        setError(body.detail ?? "Signup failed");
        return null;
      }
      return ((await res.json()) as AuthResponse).tokens;
    } catch {
      setError("Network error — check your connection");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return { isLoading, error, login, signup };
}
