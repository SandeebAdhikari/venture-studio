"use client";

import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import { formatDate, formatDuration } from "@/lib/utils";
import type { DashboardPipelineRunSummary } from "@/types/api";

interface PipelineJarvisActiveProps {
  run: DashboardPipelineRunSummary;
}

export function PipelineJarvisActive({ run }: PipelineJarvisActiveProps) {
  const reduceMotion = useReducedMotion();
  const stageTotal = run.stages_completed + run.stages_failed + run.stages_skipped;
  const progressPct =
    stageTotal > 0 ? Math.round((run.stages_completed / stageTotal) * 100) : 55;

  return (
    <motion.section
      className="jarvis-active-run relative overflow-hidden rounded-2xl border border-[hsl(187_55%_45%/0.55)] p-6 sm:p-8"
      initial={reduceMotion ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 110, damping: 20 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0 opacity-60" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-2">
          <motion.p
            className="font-mono text-[10px] uppercase tracking-[0.4em] text-[hsl(187_85%_65%)]"
            animate={reduceMotion ? undefined : { opacity: [0.45, 1, 0.45] }}
            transition={{ duration: 1.8, repeat: Infinity }}
          >
            Live orchestration
          </motion.p>
          <h2 className="text-xl font-semibold text-foreground">Active pipeline run</h2>
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge status={run.status} />
            <span className="font-mono text-xs text-muted-foreground">
              Trigger · {run.trigger}
            </span>
          </div>
          <p className="font-mono text-xs text-muted-foreground">
            Started {formatDate(run.started_at)} · {formatDuration(run.duration_ms)} elapsed
          </p>
          {run.error_summary && (
            <p className="text-sm text-destructive">{run.error_summary}</p>
          )}
        </div>

        <div className="flex items-center gap-6">
          <div className="jarvis-pipeline-ring relative flex h-32 w-32 shrink-0 items-center justify-center">
            <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 100 100" aria-hidden>
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                stroke="hsl(187 30% 22% / 0.5)"
                strokeWidth="5"
              />
              <motion.circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                stroke="hsl(187 95% 58%)"
                strokeWidth="5"
                strokeLinecap="round"
                strokeDasharray={`${progressPct * 2.64} 264`}
                animate={{ strokeDasharray: [`${progressPct * 2.64} 264`, `${progressPct * 2.64} 264`] }}
                transition={{ duration: 0.9 }}
              />
            </svg>
            <div className="text-center">
              <p className="font-mono text-2xl font-bold text-[hsl(187_92%_78%)]">{progressPct}%</p>
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                stages
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {[
              { label: "OK", value: run.stages_completed },
              { label: "Fail", value: run.stages_failed },
              { label: "Skip", value: run.stages_skipped },
            ].map((m) => (
              <div
                key={m.label}
                className="rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-black/25 px-3 py-2 text-center"
              >
                <p className="font-mono text-[9px] uppercase text-muted-foreground">{m.label}</p>
                <p className="font-mono text-lg text-[hsl(187_88%_75%)]">{m.value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.section>
  );
}
