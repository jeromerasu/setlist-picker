import { useState } from "react";
import type { TokenPair } from "@/types/api";

const API_BASE = process.env.EXPO_PUBLIC_API_BASE ?? "";

interface AppleSignInResult {
  isLoading: boolean;
  error: string | null;
  signInWithApple: () => Promise<TokenPair | null>;
}

export function useAppleSignIn(): AppleSignInResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signInWithApple = async (): Promise<TokenPair | null> => {
    setIsLoading(true);
    setError(null);
    try {
      // Apple Sign-In is handled natively via expo-apple-authentication (Wave-3).
      // In v1, the credential flow: AppleAuthentication.signInAsync() → POST /api/auth/apple
      // This stub returns null so the hook API is defined early and callers can be wired.
      const credential = await _getAppleCredential();
      if (credential === null) return null;
      const res = await fetch(`${API_BASE}/api/auth/apple`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          identity_token: credential.identity_token,
          full_name: credential.full_name,
        }),
      });
      if (!res.ok) {
        setError("Apple sign-in failed");
        return null;
      }
      return (await res.json()) as TokenPair;
    } catch {
      setError("Apple sign-in unavailable");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return { isLoading, error, signInWithApple };
}

interface AppleCredential {
  identity_token: string;
  full_name: string | null;
}

// Separated so tests can override it; real implementation calls expo-apple-authentication.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
async function _getAppleCredential(): Promise<AppleCredential | null> {
  return null;
}
