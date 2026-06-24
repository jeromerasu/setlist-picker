import { useState } from "react";
import type { TokenPair } from "@/types/api";

import { BASE_URL as API_BASE } from "../api/client";

interface GoogleSignInResult {
  isLoading: boolean;
  error: string | null;
  signInWithGoogle: () => Promise<TokenPair | null>;
}

export function useGoogleSignIn(): GoogleSignInResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signInWithGoogle = async (): Promise<TokenPair | null> => {
    setIsLoading(true);
    setError(null);
    try {
      // Google Sign-In via expo-auth-session (Wave-3 full implementation).
      // Stub: returns null so callers can be wired before the OAuth redirect flow lands.
      const credential = await _getGoogleCredential();
      if (credential === null) return null;
      const res = await fetch(`${API_BASE}/api/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: credential.id_token }),
      });
      if (!res.ok) {
        setError("Google sign-in failed");
        return null;
      }
      return (await res.json()) as TokenPair;
    } catch {
      setError("Google sign-in unavailable");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return { isLoading, error, signInWithGoogle };
}

interface GoogleCredential {
  id_token: string;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
async function _getGoogleCredential(): Promise<GoogleCredential | null> {
  return null;
}
