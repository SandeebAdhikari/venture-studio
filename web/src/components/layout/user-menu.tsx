"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DashboardRole } from "@/lib/auth/types";

interface SessionInfo {
  username: string;
  role: DashboardRole;
}

export function UserMenu() {
  const router = useRouter();
  const [session, setSession] = useState<SessionInfo | null>(null);

  useEffect(() => {
    fetch("/api/auth/session", { credentials: "include" })
      .then(async (res) => {
        if (!res.ok) {
          return null;
        }
        return (await res.json()) as SessionInfo;
      })
      .then(setSession)
      .catch(() => setSession(null));
  }, []);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    router.replace("/login");
    router.refresh();
  }

  if (!session) {
    return null;
  }

  return (
    <div className="border-t border-sidebar-muted p-4">
      <p className="truncate text-xs text-sidebar-foreground/70">{session.username}</p>
      <p className="mb-3 text-xs capitalize text-sidebar-foreground/50">{session.role}</p>
      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start gap-2 text-sidebar-foreground/80"
        onClick={logout}
      >
        <LogOut className="h-4 w-4" />
        Sign out
      </Button>
    </div>
  );
}
