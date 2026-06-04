"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { DashboardAgentStrip } from "@/components/dashboard/dashboard-agent-strip";
import { DashboardJarvisHero } from "@/components/dashboard/dashboard-jarvis-hero";
import { DashboardJarvisOpportunities } from "@/components/dashboard/dashboard-jarvis-opportunities";
import { DashboardJarvisPipeline } from "@/components/dashboard/dashboard-jarvis-pipeline";
import { useDashboardSession } from "@/components/layout/session-provider";
import { LiveIndicator, ErrorState } from "@/components/layout/page-header";
import { canAccessPage } from "@/lib/auth/rbac";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import type { DashboardOpportunitiesResponse, DashboardSummaryResponse } from "@/types/api";

const POLL_INTERVAL = 15_000;

const BOOT_SEQUENCE = [
  "Loading venture studio telemetry…",
  "Syncing pipeline orchestrator…",
  "Indexing ranked opportunities…",
  "Command center online.",
];

export default function DashboardPage() {
  const session = useDashboardSession();
  const reduceMotion = useReducedMotion();
  const summary = usePollingApi<DashboardSummaryResponse>("dashboard/summary", POLL_INTERVAL);
  const canViewAgents = !session || canAccessPage("/agents", session.role);
  const opportunities = usePollingApi<DashboardOpportunitiesResponse>(
    `dashboard/opportunities${buildQuery({ top_n: 5 })}`,
    POLL_INTERVAL,
  );
  const [bootLine, setBootLine] = useState(0);

  useEffect(() => {
    if (reduceMotion) return;
    const id = setInterval(() => {
      setBootLine((n) => (n + 1) % BOOT_SEQUENCE.length);
    }, 2400);
    return () => clearInterval(id);
  }, [reduceMotion]);

  if (summary.error) {
    return (
      <div className="jarvis-page space-y-8">
        <ErrorState message={summary.error.message} onRetry={() => summary.mutate()} />
      </div>
    );
  }

  return (
    <div className="jarvis-page space-y-8">
      <div className="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <motion.p
            className="font-mono text-[10px] uppercase tracking-[0.4em] text-[hsl(187_75%_58%)]"
            animate={reduceMotion ? undefined : { opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            Venture studio command
          </motion.p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Metrics, pipeline orchestration, agent pulse, and top-ranked opportunities.
          </p>
          {!reduceMotion && (
            <p className="mt-2 font-mono text-xs text-[hsl(187_60%_50%)]">
              &gt; {BOOT_SEQUENCE[bootLine]}
            </p>
          )}
          {summary.data?.generated_at && (
            <p className="mt-2 text-xs text-muted-foreground">
              Last updated {new Date(summary.data.generated_at).toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => summary.mutate()}
            disabled={summary.isValidating}
            className="inline-flex h-8 items-center justify-center rounded-lg border border-border bg-card px-3 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            Refresh
          </button>
          <LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />
        </div>
      </div>

      {!summary.data ? (
        <div className="space-y-6">
          <Skeleton className="h-[300px] w-full rounded-xl" />
          <div className="grid gap-6 lg:grid-cols-2">
            <Skeleton className="h-64 rounded-xl" />
            <Skeleton className="h-64 rounded-xl" />
          </div>
          <Skeleton className="h-72 w-full rounded-xl" />
        </div>
      ) : (
        <>
          <DashboardJarvisHero summary={summary.data} />

          <motion.div
            className="grid gap-6 lg:grid-cols-2"
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25 }}
          >
            <DashboardJarvisPipeline pipeline={summary.data.pipeline} />

            <motion.div
              className="jarvis-panel flex h-full flex-col rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.65)] p-6"
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.22 }}
            >
              <div className="mb-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
                  Research mesh
                </p>
                <h3 className="mt-1 text-lg font-semibold text-foreground">Agent activity</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Completion pulse across active research agents.
                </p>
              </div>
              <DashboardAgentStrip agents={(summary.data.agents ?? []).slice(0, 6)} />
              {canViewAgents && (
                <Link
                  href="/agents"
                  className="jarvis-link mt-4 font-mono text-xs uppercase tracking-wider text-[hsl(187_75%_60%)]"
                >
                  Open agent activity →
                </Link>
              )}
            </motion.div>
          </motion.div>

          <DashboardJarvisOpportunities
            data={opportunities.data}
            isLoading={!opportunities.data && !opportunities.error}
          />
        </>
      )}
    </div>
  );
}
