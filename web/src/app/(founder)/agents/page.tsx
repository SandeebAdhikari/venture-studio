"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { AgentActivityGrid } from "@/components/agents/agent-activity-grid";
import { AgentJarvisHero } from "@/components/agents/agent-jarvis-hero";
import { AgentJarvisMetrics } from "@/components/agents/agent-jarvis-metrics";
import { useDashboardSession } from "@/components/layout/session-provider";
import { LiveIndicator, PageHeader, ErrorState, EmptyState } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { usePipelineLive } from "@/hooks/use-pipeline-live";
import { usePollingApi } from "@/hooks/use-api";
import { computeAgentStepSync } from "@/lib/agents/agent-step-sync";
import { canAccessPage } from "@/lib/auth/rbac";
import type { DashboardSummaryResponse } from "@/types/api";

const POLL_IDLE_MS = 20_000;
const POLL_LIVE_MS = 5_000;

const BOOT_SEQUENCE = [
  "Initializing research mesh…",
  "Syncing agent telemetry…",
  "Mapping opportunity graph…",
  "Ready.",
];

export default function AgentsPage() {
  const router = useRouter();
  const session = useDashboardSession();
  const reduceMotion = useReducedMotion();
  const live = usePipelineLive();
  const [summaryPollMs, setSummaryPollMs] = useState(POLL_IDLE_MS);
  const summary = usePollingApi<DashboardSummaryResponse>("dashboard/summary", summaryPollMs);
  const [bootLine, setBootLine] = useState(0);

  useEffect(() => {
    setSummaryPollMs(live.isLive ? POLL_LIVE_MS : POLL_IDLE_MS);
  }, [live.isLive]);

  useEffect(() => {
    if (reduceMotion) return;
    const id = setInterval(() => {
      setBootLine((n) => (n + 1) % BOOT_SEQUENCE.length);
    }, 2200);
    return () => clearInterval(id);
  }, [reduceMotion]);

  const hasAccess = !session || canAccessPage("/agents", session.role);

  useEffect(() => {
    if (session && !canAccessPage("/agents", session.role)) {
      router.replace("/dashboard");
    }
  }, [session, router]);

  const agents = summary.data?.agents ?? [];
  const averageCoverage = summary.data?.research?.average_agent_coverage;

  const stepSync = useMemo(
    () =>
      computeAgentStepSync(
        live.pipeline?.latest_detail?.stage_runs,
        live.pipeline?.stage_order ?? [],
        agents,
        live.isLive,
        live.activeAgentKey,
      ),
    [
      live.pipeline?.latest_detail?.stage_runs,
      live.pipeline?.stage_order,
      agents,
      live.isLive,
      live.activeAgentKey,
    ],
  );

  if (session && !hasAccess) {
    return (
      <EmptyState
        title="Access restricted"
        description="Agent Activity is available to founder and admin roles. You were returned to the dashboard."
      />
    );
  }

  if (summary.error) {
    return (
      <div className="jarvis-page space-y-8">
        <PageHeader title="Agent Activity" />
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
            Venture intelligence system
          </motion.p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground">Agent Activity</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Research agent completion metrics from the backend dashboard API.
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
            onClick={() => {
              summary.mutate();
              live.mutate();
            }}
            disabled={summary.isValidating}
            className="inline-flex h-8 items-center justify-center rounded-lg border border-border bg-card px-3 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            Refresh
          </button>
          <LiveIndicator intervalSeconds={summaryPollMs / 1000} />
        </div>
      </div>

      {summary.isLoading && !summary.data ? (
        <div className="space-y-6">
          <Skeleton className="h-[280px] w-full rounded-xl" />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-44 rounded-xl" />
            ))}
          </div>
        </div>
      ) : !summary.data ? (
        <ErrorState message="Unable to load agent activity." onRetry={() => summary.mutate()} />
      ) : (
        <>
          <div className="space-y-4">
            <AgentJarvisHero agents={agents} stepSync={stepSync} />
            <AgentJarvisMetrics agents={agents} averageCoverage={averageCoverage} />
          </div>

          <motion.div
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35 }}
          >
            <AgentActivityGrid agents={agents} stepSync={stepSync} />
          </motion.div>
        </>
      )}
    </div>
  );
}
