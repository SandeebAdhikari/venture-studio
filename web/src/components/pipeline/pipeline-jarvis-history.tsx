"use client";

import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import { formatDate, formatDuration } from "@/lib/utils";
import type { DashboardPipelineRunSummary } from "@/types/api";

function runProgress(run: DashboardPipelineRunSummary): number {
  const total = run.stages_completed + run.stages_failed + run.stages_skipped;
  if (total <= 0) return run.status === "completed" ? 100 : 12;
  return Math.round((run.stages_completed / total) * 100);
}

interface PipelineJarvisHistoryProps {
  runs: DashboardPipelineRunSummary[];
  total: number;
  offset: number;
  limit: number;
  onPrev: () => void;
  onNext: () => void;
}

export function PipelineJarvisHistory({
  runs,
  total,
  offset,
  limit,
  onPrev,
  onNext,
}: PipelineJarvisHistoryProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.section
      className="jarvis-panel rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-6 sm:p-8"
      initial={reduceMotion ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
            Run archive
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">
            Orchestration history ({total})
          </h3>
        </div>
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}
        </p>
      </div>

      {runs.length === 0 ? (
        <p className="text-sm text-muted-foreground">No pipeline runs recorded.</p>
      ) : (
        <ul className="space-y-3">
          {runs.map((run, i) => {
            const pct = runProgress(run);
            return (
              <motion.li
                key={run.id}
                className="jarvis-run-row rounded-xl border border-[hsl(187_30%_26%/0.45)] bg-gradient-to-r from-[hsl(187_28%_12%/0.3)] to-transparent px-4 py-4 sm:px-5"
                initial={reduceMotion ? false : { opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                whileHover={
                  reduceMotion ? undefined : { borderColor: "hsl(187 55% 45% / 0.5)" }
                }
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={run.status} />
                      <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                        {run.trigger}
                      </span>
                    </div>
                    <p className="mt-2 font-mono text-xs text-muted-foreground">
                      {formatDate(run.started_at)} → {formatDate(run.finished_at)} ·{" "}
                      {formatDuration(run.duration_ms)}
                    </p>
                    {run.error_summary && (
                      <p className="mt-1 truncate text-xs text-destructive">{run.error_summary}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-lg text-[hsl(187_88%_75%)]">{pct}%</p>
                    <p className="font-mono text-[9px] uppercase text-muted-foreground">complete</p>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-3 font-mono text-[10px] text-muted-foreground">
                  <span>{run.stages_completed} ok</span>
                  <span>{run.stages_failed} failed</span>
                  <span>{run.stages_skipped} skipped</span>
                </div>

                <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted/80">
                  <motion.div
                    className="jarvis-score-fill h-full rounded-full"
                    initial={reduceMotion ? false : { width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.45, delay: 0.05 * i }}
                  />
                </div>
              </motion.li>
            );
          })}
        </ul>
      )}

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          className="inline-flex h-8 items-center justify-center rounded-lg border border-[hsl(187_40%_35%/0.45)] bg-card px-3 font-mono text-xs uppercase tracking-wider text-[hsl(187_75%_60%)] transition-colors hover:border-[hsl(187_60%_50%/0.6)] disabled:opacity-40"
          disabled={offset === 0}
          onClick={onPrev}
        >
          Previous
        </button>
        <button
          type="button"
          className="inline-flex h-8 items-center justify-center rounded-lg border border-[hsl(187_40%_35%/0.45)] bg-card px-3 font-mono text-xs uppercase tracking-wider text-[hsl(187_75%_60%)] transition-colors hover:border-[hsl(187_60%_50%/0.6)] disabled:opacity-40"
          disabled={offset + limit >= total}
          onClick={onNext}
        >
          Next
        </button>
      </div>
    </motion.section>
  );
}
