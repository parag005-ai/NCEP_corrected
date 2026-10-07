"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import type { Session } from "@/types";
import {
  getCurrentSession,
  getRedirectPath,
  getServiceErrorMessage,
  login as doLogin,
  logout as doLogout,
} from "@/services";
import { useRouter } from "next/navigation";

type AuthContextValue = {
  session: Session | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue>({
  session: null,
  loading: true,
  login: async () => ({ ok: false, error: "Not initialised" }),
  logout: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let active = true;
    const initAuth = async () => {
      try {
        const s = await getCurrentSession();
        if (active) setSession(s);
      } catch {
        // The login screen remains available if storage/API session recovery
        // fails; login() returns a user-facing error for subsequent attempts.
        if (active) setSession(null);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    void initAuth();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      try {
        const result = await doLogin(email, password);
        if (result.ok) {
          setSession(result.session);
          router.push(getRedirectPath(result.session.role));
          return { ok: true as const };
        }
        return { ok: false as const, error: result.error };
      } catch (error) {
        return { ok: false as const, error: getServiceErrorMessage(error) };
      }
    },
    [router],
  );

  const logout = useCallback(async () => {
    try {
      await doLogout();
    } finally {
      setSession(null);
      router.push("/login");
    }
  }, [router]);

  return (
    <AuthContext.Provider value={{ session, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
