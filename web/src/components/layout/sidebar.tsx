"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  CheckSquare,
  FileText,
  LayoutDashboard,
  Menu,
  Target,
  Wallet,
  Workflow,
  X,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { UserMenu } from "@/components/layout/user-menu";
import type { DashboardRole } from "@/lib/auth/types";

const VIEWER_NAV_HREFS = new Set(["/dashboard", "/reports", "/budget", "/opportunities"]);

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/opportunities", label: "Opportunities", icon: Target },
  { href: "/pipeline", label: "Pipeline", icon: Workflow },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/budget", label: "Budget", icon: Wallet },
  { href: "/agents", label: "Agent Activity", icon: Activity },
];

function navItemsForRole(role: DashboardRole | null) {
  if (!role || role === "founder") {
    return navItems;
  }
  if (role === "admin") {
    return navItems;
  }
  return navItems.filter((item) => VIEWER_NAV_HREFS.has(item.href));
}

export function Sidebar({ role }: { role?: DashboardRole | null }) {
  const pathname = usePathname();
  const items = navItemsForRole(role ?? null);

  return (
    <aside className="hidden h-full w-64 shrink-0 flex-col bg-sidebar text-sidebar-foreground md:flex">
      <div className="border-b border-sidebar-muted px-6 py-5">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-6 w-6 text-primary" />
          <div>
            <p className="text-sm font-semibold">Venture Studio</p>
            <p className="text-xs text-sidebar-foreground/70">Founder Dashboard</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-muted font-medium text-white"
                  : "text-sidebar-foreground/80 hover:bg-sidebar-muted hover:text-white",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <UserMenu />
    </aside>
  );
}

export function MobileNav({ role }: { role?: DashboardRole | null }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const items = navItemsForRole(role ?? null);

  return (
    <div className="border-b border-border bg-card md:hidden">
      <div className="flex items-center justify-between px-4 py-3">
        <div>
          <p className="text-sm font-semibold">Venture Studio</p>
          <p className="text-xs text-muted-foreground">Founder Dashboard</p>
        </div>
        <Button variant="ghost" size="icon" onClick={() => setOpen((v) => !v)} aria-label="Toggle menu">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>
      {open && (
        <nav className="space-y-1 border-t border-border px-2 py-2">
          {items.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm",
                  active ? "bg-accent font-medium" : "text-muted-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}
