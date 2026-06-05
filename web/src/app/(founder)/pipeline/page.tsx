"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { PipelineJarvisActive } from "@/components/pipeline/pipeline-jarvis-active";
import { PipelineJarvisHero } from "@/components/pipeline/pipeline-jarvis-hero";
import { PipelineJarvisMetrics } from "@/components/pipeline/pipeline-jarvis-metrics";
import { PipelineJarvisHistory } from "@/components/pipeline/pipeline-jarvis-history";
import { PipelineJarvisStages } from "@/components/pipeline/pipeline-jarvis-stages";
import { LiveIndicator, ErrorState } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import type { DashboardPipelineResponse } from "@/types/api";

const POLL_IDLE_MS = 10_000;
const POLL_LIVE_MS = 3_000;

const BOOT_SEQUENCE = [
  "Connecting to orchestrator…",
  "Loading stage graph…",
  "Syncing run telemetry…",
  "Pipeline console online.",
];

export default function PipelinePage() {
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const reduceMotion = useReducedMotion();
  const [bootLine, setBootLine] = useState(0);
  const [pollMs, setPollMs] = useState(POLL_IDLE_MS);

  const pipeline = usePollingApi<DashboardPipelineResponse>(
    `dashboard/pipeline${buildQuery({ limit, offset, include_stages: true })}`,
    pollMs,
  );

  useEffect(() => {
    setPollMs(pipeline.data?.running ? POLL_LIVE_MS : POLL_IDLE_MS);
  }, [pipeline.data?.running]);

  useEffect(() => {
    if (reduceMotion) return;
    const id = setInterval(() => {
      setBootLine((n) => (n + 1) % BOOT_SEQUENCE.length);
    }, 2200);
    return () => clearInterval(id);
  }, [reduceMotion]);

  if (pipeline.error) {
    return (
      <div className="jarvis-page space-y-8">
        <ErrorState message={pipeline.error.message} onRetry={() => pipeline.mutate()} />
      </div>
    );
  }

  const runs = pipeline.data?.runs.items ?? [];
  const total = pipeline.data?.runs.total ?? 0;

  return (
    <div className="jarvis-page space-y-8">
      <div className="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <motion.p
            className="font-mono text-[10px] uppercase tracking-[0.4em] text-[hsl(187_75%_58%)]"
            animate={reduceMotion ? undefined : { opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            Orchestration control
          </motion.p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground">Pipeline</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Monitor pipeline runs and stage-level execution from the backend orchestrator.
          </p>
          {!reduceMotion && (
            <p className="mt-2 font-mono text-xs text-[hsl(187_60%_50%)]">
              &gt; {BOOT_SEQUENCE[bootLine]}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => pipeline.mutate()}
            disabled={pipeline.isValidating}
            className="inline-flex h-8 items-center justify-center rounded-lg border border-border bg-card px-3 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            Refresh
          </button>
          <LiveIndicator intervalSeconds={pollMs / 1000} />
        </div>
      </div>

      {!pipeline.data ? (
        <div className="space-y-6">
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-96 w-full rounded-xl" />
          <Skeleton className="h-72 w-full rounded-xl" />
        </div>
      ) : (
        <>
          <div className="space-y-4">
            <PipelineJarvisHero data={pipeline.data} />
            <PipelineJarvisMetrics data={pipeline.data} />
          </div>

          {pipeline.data.running && <PipelineJarvisActive run={pipeline.data.running} />}

          {pipeline.data.latest_detail && (
            <motion.section
              className="jarvis-panel jarvis-pipeline-panel rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-6 sm:p-8 lg:p-10"
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
            >
              <div className="mb-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
                  Latest execution
                </p>
                <h3 className="mt-1 text-lg font-semibold text-foreground">Stage breakdown</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Select a stage on the filmstrip to inspect details.
                </p>
              </div>

              <PipelineJarvisStages
                stages={pipeline.data.latest_detail.stage_runs}
                stageOrder={pipeline.data.stage_order}
                isLive={!!pipeline.data.running}
                runningRunId={pipeline.data.running?.id ?? null}
              />
            </motion.section>
          )}

          <PipelineJarvisHistory
            runs={runs}
            total={total}
            offset={offset}
            limit={limit}
            onPrev={() => setOffset(Math.max(0, offset - limit))}
            onNext={() => setOffset(offset + limit)}
          />
        </>
      )}
    </div>
  );
}
