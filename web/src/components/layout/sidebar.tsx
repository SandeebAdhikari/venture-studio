"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  CheckSquare,
  FileText,
  LayoutDashboard,
  LayoutGrid,
  Menu,
  Target,
  Wallet,
  Workflow,
  X,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/theme-toggle";
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
  if (!role || role === "founder" || role === "admin") {
    return navItems;
  }
  return navItems.filter((item) => VIEWER_NAV_HREFS.has(item.href));
}

export function Sidebar({
  role,
  className,
}: {
  role?: DashboardRole | null;
  className?: string;
}) {
  const pathname = usePathname();
  const items = navItemsForRole(role ?? null);

  return (
    <aside
      className={cn(
        "hidden h-full w-64 shrink-0 flex-col border-r border-sidebar-muted bg-sidebar text-sidebar-foreground md:flex",
        className,
      )}
    >
      <div className="border-b border-sidebar-muted px-5 py-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <LayoutGrid className="h-5 w-5 shrink-0" />
            <div>
              <p className="text-sm font-semibold leading-tight">Venture Studio</p>
              <p className="text-xs text-sidebar-foreground/55">
                Elegant ops in black &amp; white
              </p>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 p-3">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                active
                  ? "bg-primary font-medium text-primary-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-muted hover:text-sidebar-foreground",
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
    <div className="relative z-10 border-b border-border bg-card md:hidden">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <LayoutGrid className="h-5 w-5" />
          <div>
            <p className="text-sm font-semibold">Venture Studio</p>
            <p className="text-xs text-muted-foreground">Founder Dashboard</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button variant="ghost" size="icon" onClick={() => setOpen((v) => !v)} aria-label="Toggle menu">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>
      {open && (
        <nav className="space-y-0.5 border-t border-border px-2 py-2">
          {items.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm",
                  active
                    ? "bg-primary font-medium text-primary-foreground"
                    : "text-muted-foreground",
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
