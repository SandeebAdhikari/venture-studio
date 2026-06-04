"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Badge, statusVariant } from "@/components/ui/badge";
import {
  formatStageName,
  orderPipelineStages,
  stageShortLabel,
} from "@/lib/pipeline/stage-order";
import { formatDuration } from "@/lib/utils";
import type { DashboardPipelineStageSummary, PipelineStageStatus } from "@/types/api";

function stageTone(status: PipelineStageStatus): string {
  switch (status) {
    case "completed":
      return "jarvis-stage-node--completed";
    case "running":
      return "jarvis-stage-node--running";
    case "failed":
      return "jarvis-stage-node--failed";
    case "skipped":
      return "jarvis-stage-node--skipped";
    default:
      return "jarvis-stage-node--pending";
  }
}

function defaultSelected(
  ordered: DashboardPipelineStageSummary[],
): DashboardPipelineStageSummary | null {
  if (ordered.length === 0) return null;
  return (
    ordered.find((s) => s.status === "running") ??
    ordered.find((s) => s.status === "failed") ??
    ordered[ordered.length - 1]
  );
}

interface PipelineJarvisStagesProps {
  stages: DashboardPipelineStageSummary[];
  stageOrder: string[];
}

export function PipelineJarvisStages({ stages, stageOrder }: PipelineJarvisStagesProps) {
  const reduceMotion = useReducedMotion();
  const ordered = useMemo(
    () => orderPipelineStages(stages, stageOrder),
    [stages, stageOrder],
  );
  const completed = ordered.filter((s) => s.status === "completed").length;
  const progressPct =
    ordered.length > 0 ? Math.round((completed / ordered.length) * 100) : 0;

  const [selectedStage, setSelectedStage] = useState<string | null>(null);
  const activeKey = selectedStage ?? defaultSelected(ordered)?.stage ?? null;
  const active = ordered.find((s) => s.stage === activeKey) ?? null;

  useEffect(() => {
    const pick = defaultSelected(ordered);
    if (!pick) return;
    setSelectedStage((prev) => {
      if (prev && ordered.some((s) => s.stage === prev)) return prev;
      return pick.stage;
    });
  }, [ordered]);

  return (
    <div className="jarvis-pipeline-stages">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-muted-foreground">
          {completed} of {ordered.length} stages complete
        </p>
        <div className="flex min-w-[160px] items-center gap-3">
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted/80">
            <motion.div
              className="jarvis-score-fill h-full rounded-full"
              initial={reduceMotion ? false : { width: 0 }}
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: 0.6 }}
            />
          </div>
          <span className="font-mono text-xs text-[hsl(187_85%_72%)]">{progressPct}%</span>
        </div>
      </div>

      {/* Filmstrip — tap a stage to inspect */}
      <div
        className="jarvis-stage-filmstrip relative mb-6 rounded-xl border border-[hsl(187_35%_28%/0.35)] bg-[hsl(187_22%_8%/0.35)] px-3 py-4 sm:px-4"
        style={{ "--stage-count": ordered.length } as CSSProperties}
      >
        <div
          className="jarvis-filmstrip-grid relative"
          role="tablist"
          aria-label="Pipeline stages"
        >
          <div className="jarvis-filmstrip-track pointer-events-none absolute inset-x-0 top-[1.125rem] z-0 hidden h-px sm:block" />
          {ordered.map((stage, index) => {
            const isActive = stage.stage === activeKey;
            const inProcess = stage.status === "running";
            return (
              <button
                key={stage.stage}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setSelectedStage(stage.stage)}
                className="jarvis-filmstrip-node group relative z-10"
                aria-label={`${formatStageName(stage.stage)}, ${stage.status}`}
              >
                <span
                  className={`jarvis-stage-node relative mx-auto flex h-9 w-9 shrink-0 items-center justify-center rounded-full border font-mono text-[10px] font-semibold ${stageTone(stage.status)} ${
                    isActive ? "jarvis-stage-node--focus" : ""
                  } ${inProcess ? "jarvis-stage-node--process" : ""}`}
                >
                  {String(index + 1).padStart(2, "0")}
                  {inProcess && !reduceMotion && (
                    <span className="jarvis-stage-ping absolute inset-0 rounded-full" aria-hidden />
                  )}
                </span>
                <span
                  className="jarvis-filmstrip-label mt-2 block w-full text-center font-mono text-[8px] uppercase leading-tight tracking-wide text-muted-foreground group-hover:text-foreground sm:text-[9px]"
                  title={formatStageName(stage.stage)}
                >
                  {stageShortLabel(stage.stage)}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Single detail lens — only the selected stage expands */}
      {active ? (
        <StageDetailLens stage={active} reduceMotion={!!reduceMotion} />
      ) : (
        <p className="text-sm text-muted-foreground">No stage data available.</p>
      )}

      {/* Compact index — scan all stages without visual noise */}
      <ul className="mt-6 space-y-1 border-t border-border/50 pt-5" aria-label="Stage index">
        {ordered.map((stage) => {
          const isActive = stage.stage === activeKey;
          return (
            <li key={stage.stage}>
              <button
                type="button"
                onClick={() => setSelectedStage(stage.stage)}
                className={`jarvis-stage-index-row flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
                  isActive ? "jarvis-stage-index-row--active" : ""
                }`}
              >
                <span
                  className={`h-2 w-2 shrink-0 rounded-full ${
                    stage.status === "completed"
                      ? "bg-[hsl(187_90%_55%)]"
                      : stage.status === "running"
                        ? "bg-[hsl(187_95%_65%)] shadow-[0_0_8px_hsl(187_90%_60%)]"
                        : stage.status === "failed"
                          ? "bg-destructive"
                          : "bg-muted-foreground/40"
                  }`}
                  aria-hidden
                />
                <span className="min-w-0 flex-1 truncate text-sm capitalize text-foreground">
                  {formatStageName(stage.stage)}
                </span>
                <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                  {formatDuration(stage.duration_ms)}
                </span>
                <Badge variant={statusVariant(stage.status)} className="shrink-0 text-[10px]">
                  {stage.status}
                </Badge>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function StageDetailLens({
  stage,
  reduceMotion,
}: {
  stage: DashboardPipelineStageSummary;
  reduceMotion: boolean;
}) {
  const flow =
    stage.items_in > 0
      ? `${stage.items_in} in → ${stage.items_out} out`
      : `${stage.records_processed} processed`;

  return (
    <motion.div
      key={stage.stage}
      className="jarvis-stage-lens relative overflow-hidden rounded-2xl border border-[hsl(187_40%_32%/0.45)] bg-gradient-to-br from-[hsl(187_26%_11%/0.55)] to-transparent p-6"
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 24 }}
    >
      <div className="jarvis-hero-glow pointer-events-none absolute -right-20 -top-20 h-40 w-40 opacity-40" aria-hidden />

      <div className="relative flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
            Inspecting
          </p>
          <h4 className="mt-1 text-lg font-semibold capitalize text-foreground">
            {formatStageName(stage.stage)}
          </h4>
          <p className="mt-1 font-mono text-sm text-[hsl(187_80%_68%)]">{flow}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={statusVariant(stage.status)}>{stage.status}</Badge>
          <span className="font-mono text-xs text-muted-foreground">
            {formatDuration(stage.duration_ms)}
          </span>
        </div>
      </div>

      {stage.error_detail && (
        <p className="relative mt-4 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {stage.error_detail}
        </p>
      )}

      <div className="relative mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Items in", value: stage.items_in },
          { label: "Items out", value: stage.items_out },
          { label: "Failed", value: stage.items_failed },
          { label: "Processed", value: stage.records_processed },
        ].map((m) => (
          <div
            key={m.label}
            className="rounded-lg border border-[hsl(187_38%_30%/0.25)] bg-black/15 px-3 py-2.5 text-center"
          >
            <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
              {m.label}
            </p>
            <p className="mt-0.5 font-mono text-base text-[hsl(187_88%_76%)]">{m.value}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
