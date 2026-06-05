"use client";

import Link from "next/link";
import { ChevronDown } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import { cn, formatDate } from "@/lib/utils";
import type { PipelineLiveProgress } from "@/lib/pipeline/stage-sync";
import type { DashboardSummaryResponse } from "@/types/api";

interface DashboardJarvisPipelineProps {
  pipeline: DashboardSummaryResponse["pipeline"];
  liveProgress?: PipelineLiveProgress | null;
  isLive?: boolean;
  expanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
}

const COLLAPSED_STAGE_COUNT = 2;

function stageLabel(stage: string): string {
  return stage
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function PipelineProgressRing({
  progressPct,
  running,
  isLive,
  reduceMotion,
  compact = false,
}: {
  progressPct: number;
  running: boolean;
  isLive: boolean;
  reduceMotion: boolean;
  compact?: boolean;
}) {
  const size = compact ? "h-20 w-20" : "h-28 w-28";
  const labelSize = compact ? "text-lg" : "text-2xl";

  return (
    <div className={cn("jarvis-pipeline-ring relative flex shrink-0 items-center justify-center", size)}>
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
      <span className={cn("font-mono font-semibold text-[hsl(187_90%_75%)]", labelSize)}>
        {running || isLive ? "RUN" : progressPct || "—"}
      </span>
    </div>
  );
}

export function DashboardJarvisPipeline({
  pipeline,
  liveProgress,
  isLive = false,
  expanded = false,
  onExpandedChange,
}: DashboardJarvisPipelineProps) {
  const reduceMotion = useReducedMotion();
  const running = pipeline.running;
  const latest = pipeline.latest;
  const stageTotal =
    latest != null ? latest.stages_completed + latest.stages_failed : 0;
  const progressPct = isLive && liveProgress
    ? liveProgress.progressPct
    : stageTotal > 0 && latest
      ? Math.round((latest.stages_completed / stageTotal) * 100)
      : running
        ? 42
        : 0;

  const stageRows = liveProgress?.ordered ?? [];
  const canExpand = onExpandedChange != null;
  const previewStages = stageRows.slice(0, COLLAPSED_STAGE_COUNT);

  return (
    <motion.div
      className={cn(
        "jarvis-panel flex w-full flex-col rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.65)] p-6",
        expanded ? "h-fit self-start" : "h-full min-h-0",
      )}
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <div className="shrink-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
              Orchestration
            </p>
            <h3 className="mt-1 text-lg font-semibold text-foreground">Pipeline status</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Venture pipeline orchestration and latest run telemetry.
            </p>
          </div>
          <span
            className={`jarvis-status-pill shrink-0 rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider ${
              running || isLive ? "jarvis-status-pill--active" : "jarvis-status-pill--idle"
            }`}
          >
            {running || isLive ? "live" : "standby"}
          </span>
        </div>
      </div>

      <div className="mt-4 flex min-h-0 flex-1 flex-col">
        {expanded ? (
          <div className="flex flex-col">
            <PipelineProgressRing
              progressPct={progressPct}
              running={!!running}
              isLive={isLive}
              reduceMotion={!!reduceMotion}
            />

            {running ? (
              <div className="mt-4 rounded-xl border border-[hsl(187_50%_40%/0.35)] bg-black/25 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Running</span>
                  <StatusBadge status={running.status} />
                </div>
                <p className="mt-2 font-mono text-xs text-muted-foreground">
                  Started {formatDate(running.started_at)}
                </p>
                {liveProgress?.runningStage && (
                  <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-[hsl(187_75%_60%)]">
                    Stage · {stageLabel(liveProgress.runningStage.stage)}
                  </p>
                )}
              </div>
            ) : (
              <p className="mt-4 text-center text-sm text-muted-foreground">
                No pipeline run in progress.
              </p>
            )}

            {latest && (
              <div className="mt-4 rounded-lg border border-border/60 bg-muted/20 p-4 text-sm">
                <p className="font-medium">Latest run</p>
                <p className="mt-1 text-muted-foreground">
                  {latest.stages_completed} completed · {latest.stages_failed} failed
                </p>
              </div>
            )}

            {stageRows.length > 0 && (
              <div className="mt-4 space-y-1.5">
                <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  Research stages
                </p>
                <div className="grid grid-cols-2 gap-1.5">
                  {stageRows.map((stage) => (
                    <div
                      key={stage.stage}
                      className={`rounded-md border px-2 py-1.5 font-mono text-[10px] uppercase tracking-wide ${
                        stage.status === "running"
                          ? "border-[hsl(187_55%_50%/0.65)] bg-[hsl(187_30%_14%/0.4)] text-[hsl(187_90%_75%)]"
                          : stage.status === "completed"
                            ? "border-[hsl(187_35%_28%/0.35)] bg-[hsl(187_22%_10%/0.35)] text-muted-foreground"
                            : "border-[hsl(187_35%_28%/0.25)] bg-[hsl(187_20%_8%/0.25)] text-muted-foreground/80"
                      }`}
                    >
                      {stageLabel(stage.stage)}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {canExpand && (
              <button
                type="button"
                onClick={() => onExpandedChange?.(false)}
                className="mt-4 flex w-full shrink-0 items-center justify-center gap-1.5 rounded-lg border border-[hsl(187_35%_28%/0.4)] bg-[hsl(187_24%_10%/0.25)] py-2 font-mono text-[10px] uppercase tracking-wider text-[hsl(187_75%_60%)] transition-colors hover:border-[hsl(187_55%_45%/0.55)] hover:text-[hsl(187_85%_72%)]"
              >
                Show less
                <ChevronDown className="h-3.5 w-3.5 rotate-180" aria-hidden />
              </button>
            )}
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex items-start gap-4">
              <PipelineProgressRing
                progressPct={progressPct}
                running={!!running}
                isLive={isLive}
                reduceMotion={!!reduceMotion}
                compact
              />

              <div className="min-w-0 flex-1 space-y-3 pt-1">
                {running ? (
                  <div className="rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-black/25 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium">Running</span>
                      <StatusBadge status={running.status} />
                    </div>
                    <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">
                      Started {formatDate(running.started_at)}
                    </p>
                    {liveProgress?.runningStage && (
                      <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-[hsl(187_75%_60%)]">
                        Stage · {stageLabel(liveProgress.runningStage.stage)}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No pipeline run in progress.</p>
                )}

                {latest && (
                  <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
                    <p className="font-medium">Latest run</p>
                    <p className="mt-1 text-muted-foreground">
                      {latest.stages_completed} completed · {latest.stages_failed} failed
                    </p>
                  </div>
                )}

                {previewStages.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Research stages
                    </p>
                    <div className="grid grid-cols-1 gap-1.5">
                      {previewStages.map((stage) => (
                        <div
                          key={stage.stage}
                          className={`rounded-md border px-2 py-1.5 font-mono text-[10px] uppercase tracking-wide ${
                            stage.status === "running"
                              ? "border-[hsl(187_55%_50%/0.65)] bg-[hsl(187_30%_14%/0.4)] text-[hsl(187_90%_75%)]"
                              : stage.status === "completed"
                                ? "border-[hsl(187_35%_28%/0.35)] bg-[hsl(187_22%_10%/0.35)] text-muted-foreground"
                                : "border-[hsl(187_35%_28%/0.25)] bg-[hsl(187_20%_8%/0.25)] text-muted-foreground/80"
                          }`}
                        >
                          {stageLabel(stage.stage)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {canExpand && (
              <button
                type="button"
                onClick={() => onExpandedChange?.(!expanded)}
                className="mt-4 flex w-full shrink-0 items-center justify-center gap-1.5 rounded-lg border border-[hsl(187_35%_28%/0.4)] bg-[hsl(187_24%_10%/0.25)] py-2 font-mono text-[10px] uppercase tracking-wider text-[hsl(187_75%_60%)] transition-colors hover:border-[hsl(187_55%_45%/0.55)] hover:text-[hsl(187_85%_72%)]"
              >
                Show full pipeline
                <ChevronDown className="h-3.5 w-3.5" aria-hidden />
              </button>
            )}

            {!expanded && <div className="min-h-0 flex-1" aria-hidden />}
          </div>
        )}
      </div>

      <Link
        href="/pipeline"
        className="jarvis-link mt-auto shrink-0 pt-5 font-mono text-xs uppercase tracking-wider text-[hsl(187_75%_60%)]"
      >
        Open pipeline →
      </Link>
    </motion.div>
  );
}
