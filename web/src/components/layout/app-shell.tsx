"use client";

import { Sidebar, MobileNav } from "@/components/layout/sidebar";
import { SessionProvider, useDashboardSession } from "@/components/layout/session-provider";

function ShellContent({ children }: { children: React.ReactNode }) {
  const session = useDashboardSession();
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar role={session?.role ?? null} />
      <div className="flex min-w-0 flex-1 flex-col">
        <MobileNav role={session?.role ?? null} />
        <main className="flex-1 overflow-auto p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ShellContent>{children}</ShellContent>
    </SessionProvider>
  );
}
