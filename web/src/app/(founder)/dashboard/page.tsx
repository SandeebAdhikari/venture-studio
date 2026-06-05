"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { DashboardJarvisAgentActivity } from "@/components/dashboard/dashboard-jarvis-agent-activity";
import { DashboardJarvisHero } from "@/components/dashboard/dashboard-jarvis-hero";
import { DashboardJarvisMetrics } from "@/components/dashboard/dashboard-jarvis-metrics";
import { DashboardJarvisOpportunities } from "@/components/dashboard/dashboard-jarvis-opportunities";
import { DashboardJarvisPipeline } from "@/components/dashboard/dashboard-jarvis-pipeline";
import { useDashboardSession } from "@/components/layout/session-provider";
import { LiveIndicator, ErrorState } from "@/components/layout/page-header";
import { canAccessPage } from "@/lib/auth/rbac";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { usePipelineLive } from "@/hooks/use-pipeline-live";
import { computeAgentStepSync, agentKeyForStep } from "@/lib/agents/agent-step-sync";
import { buildQuery } from "@/lib/api/client";
import { resolveDashboardAgents } from "@/lib/dashboard/agents";
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
  const live = usePipelineLive(!!summary.data);
  const [pipelineExpanded, setPipelineExpanded] = useState(false);
  const [agentsExpanded, setAgentsExpanded] = useState(false);
  const [bootLine, setBootLine] = useState(0);

  const agents = useMemo(
    () => (summary.data ? resolveDashboardAgents(summary.data) : []),
    [summary.data],
  );

  const stepSync = useMemo(
    () =>
      summary.data
        ? computeAgentStepSync(
            live.pipeline?.latest_detail?.stage_runs,
            live.pipeline?.stage_order ?? [],
            agents,
            live.isLive,
            live.activeAgentKey,
          )
        : null,
    [
      summary.data,
      live.pipeline?.latest_detail?.stage_runs,
      live.pipeline?.stage_order,
      agents,
      live.isLive,
      live.activeAgentKey,
    ],
  );

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
          <div className="space-y-4">
            <DashboardJarvisHero summary={summary.data} />
            <DashboardJarvisMetrics summary={summary.data} />
          </div>

          <motion.div
            className={`grid gap-6 lg:grid-cols-2 ${
              pipelineExpanded || agentsExpanded ? "items-start" : "items-stretch"
            }`}
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25 }}
          >
            <DashboardJarvisPipeline
              pipeline={summary.data.pipeline}
              liveProgress={live.progress}
              isLive={live.isLive}
              expanded={pipelineExpanded}
              onExpandedChange={setPipelineExpanded}
            />

            <DashboardJarvisAgentActivity
              agents={agents}
              activeAgentKey={
                stepSync?.activeStep != null ? agentKeyForStep(stepSync.activeStep) : null
              }
              canViewAgents={canViewAgents}
              expanded={agentsExpanded}
              onExpandedChange={setAgentsExpanded}
            />
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
