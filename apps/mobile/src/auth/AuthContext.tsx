import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { getTokens, setTokens, clearTokens } from "./token-store";
import type { TokenPair } from "@/types/api";

interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextValue extends AuthState {
  signIn: (pair: TokenPair) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({ isLoading: true, isAuthenticated: false });

  useEffect(() => {
    getTokens()
      .then((pair) => setState({ isLoading: false, isAuthenticated: pair !== null }))
      .catch(() => setState({ isLoading: false, isAuthenticated: false }));
  }, []);

  const signIn = useCallback(async (pair: TokenPair) => {
    await setTokens(pair);
    setState({ isLoading: false, isAuthenticated: true });
  }, []);

  const signOut = useCallback(async () => {
    await clearTokens();
    setState({ isLoading: false, isAuthenticated: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === null) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
