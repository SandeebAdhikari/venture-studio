"use client";

import { Sidebar, MobileNav } from "@/components/layout/sidebar";
import { SessionProvider, useDashboardSession } from "@/components/layout/session-provider";
import { VentureNetworkBackdrop } from "@/components/visuals/venture-network-backdrop";

function ShellContent({ children }: { children: React.ReactNode }) {
  const session = useDashboardSession();
  return (
    <div className="dashboard-canvas relative flex min-h-screen">
      <Sidebar role={session?.role ?? null} className="relative z-10" />
      <div className="relative flex min-w-0 flex-1 flex-col">
        <VentureNetworkBackdrop />
        <MobileNav role={session?.role ?? null} />
        <main className="relative z-10 flex-1 overflow-auto p-4 sm:p-6 lg:p-8 xl:p-10">
          {children}
        </main>
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
