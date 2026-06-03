"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { DashboardRole } from "@/lib/auth/types";

interface SessionState {
  username: string;
  role: DashboardRole;
}

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState | null>(null);

  useEffect(() => {
    fetch("/api/auth/session", { credentials: "include" })
      .then(async (res) => (res.ok ? ((await res.json()) as SessionState) : null))
      .then(setSession)
      .catch(() => setSession(null));
  }, []);

  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export function useDashboardSession(): SessionState | null {
  return useContext(SessionContext);
}
