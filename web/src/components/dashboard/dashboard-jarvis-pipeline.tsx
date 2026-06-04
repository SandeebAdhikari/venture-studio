"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import { formatDate } from "@/lib/utils";
import type { DashboardSummaryResponse } from "@/types/api";

interface DashboardJarvisPipelineProps {
  pipeline: DashboardSummaryResponse["pipeline"];
}

export function DashboardJarvisPipeline({ pipeline }: DashboardJarvisPipelineProps) {
  const reduceMotion = useReducedMotion();
  const running = pipeline.running;
  const latest = pipeline.latest;
  const stageTotal =
    latest != null ? latest.stages_completed + latest.stages_failed : 0;
  const progressPct =
    stageTotal > 0 && latest
      ? Math.round((latest.stages_completed / stageTotal) * 100)
      : running
        ? 42
        : 0;

  return (
    <motion.div
      className="jarvis-panel flex h-full flex-col rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.65)] p-6"
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <div className="mb-4 flex items-start justify-between gap-2">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
            Orchestration
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">Pipeline status</h3>
        </div>
        <span
          className={`jarvis-status-pill rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider ${
            running ? "jarvis-status-pill--active" : "jarvis-status-pill--idle"
          }`}
        >
          {running ? "live" : "standby"}
        </span>
      </div>

      <div className="jarvis-pipeline-ring relative mx-auto mb-5 flex h-28 w-28 items-center justify-center">
        <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 100 100" aria-hidden>
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke="hsl(187 30% 22% / 0.5)"
            strokeWidth="4"
          />
          <motion.circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke="hsl(187 90% 55%)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={`${progressPct * 2.64} 264`}
            initial={reduceMotion ? false : { strokeDasharray: "0 264" }}
            animate={{ strokeDasharray: `${progressPct * 2.64} 264` }}
            transition={{ duration: 0.8 }}
          />
        </svg>
        <span className="font-mono text-2xl font-semibold text-[hsl(187_90%_75%)]">
          {running ? "RUN" : progressPct || "—"}
        </span>
      </div>

      {running ? (
        <div className="rounded-xl border border-[hsl(187_50%_40%/0.35)] bg-black/25 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Running</span>
            <StatusBadge status={running.status} />
          </div>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            Started {formatDate(running.started_at)}
          </p>
        </div>
      ) : (
        <p className="text-center text-sm text-muted-foreground">No pipeline run in progress.</p>
      )}

      {latest && (
        <div className="mt-4 rounded-lg border border-border/60 bg-muted/20 p-4 text-sm">
          <p className="font-medium">Latest run</p>
          <p className="mt-1 text-muted-foreground">
            {latest.stages_completed} completed · {latest.stages_failed} failed
          </p>
        </div>
      )}

      <Link
        href="/pipeline"
        className="jarvis-link mt-auto pt-5 font-mono text-xs uppercase tracking-wider text-[hsl(187_75%_60%)]"
      >
        Open pipeline →
      </Link>
    </motion.div>
  );
}
