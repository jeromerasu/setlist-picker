import { useState } from "react";
import type { TokenPair } from "@/types/api";

const API_BASE = process.env.EXPO_PUBLIC_API_BASE ?? "";

interface LocalAuthResult {
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<TokenPair | null>;
  signup: (username: string, password: string, display_name: string) => Promise<TokenPair | null>;
}

export function useLocalAuth(): LocalAuthResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = async (username: string, password: string): Promise<TokenPair | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const body = (await res.json()) as { detail?: string };
        setError(body.detail ?? "Login failed");
        return null;
      }
      return (await res.json()) as TokenPair;
    } catch {
      setError("Network error — check your connection");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (
    username: string,
    password: string,
    display_name: string
  ): Promise<TokenPair | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, display_name }),
      });
      if (!res.ok) {
        const body = (await res.json()) as { detail?: string };
        setError(body.detail ?? "Signup failed");
        return null;
      }
      return (await res.json()) as TokenPair;
    } catch {
      setError("Network error — check your connection");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return { isLoading, error, login, signup };
}
