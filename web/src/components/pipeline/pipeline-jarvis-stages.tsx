"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { ChevronDown } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { Badge, statusVariant } from "@/components/ui/badge";
import {
  computePipelineLiveProgress,
  stageTone,
} from "@/lib/pipeline/stage-sync";
import {
  formatStageName,
  stageShortLabel,
} from "@/lib/pipeline/stage-order";
import { cn, formatDuration } from "@/lib/utils";
import type { DashboardPipelineStageSummary } from "@/types/api";

/** Stages through this step are shown in the index list when collapsed. Filmstrip always shows all stages. */
const COLLAPSED_STAGE_UP_TO = "market_research";

function visibleStages(
  ordered: DashboardPipelineStageSummary[],
  expanded: boolean,
): DashboardPipelineStageSummary[] {
  if (expanded) return ordered;
  const cutoff = ordered.findIndex((stage) => stage.stage === COLLAPSED_STAGE_UP_TO);
  if (cutoff === -1) return ordered;
  return ordered.slice(0, cutoff + 1);
}

function defaultSelected(
  ordered: DashboardPipelineStageSummary[],
): DashboardPipelineStageSummary | null {
  if (ordered.length === 0) return null;
  const lastCompleted = [...ordered].reverse().find((s) => s.status === "completed");
  return (
    ordered.find((s) => s.status === "running") ??
    ordered.find((s) => s.status === "failed") ??
    lastCompleted ??
    ordered.find((s) => s.status === "pending") ??
    ordered[0]
  );
}

interface PipelineJarvisStagesProps {
  stages: DashboardPipelineStageSummary[];
  stageOrder: string[];
  isLive?: boolean;
  runningRunId?: string | null;
}

export function PipelineJarvisStages({
  stages,
  stageOrder,
  isLive = false,
  runningRunId,
}: PipelineJarvisStagesProps) {
  const reduceMotion = useReducedMotion();
  const live = useMemo(
    () => computePipelineLiveProgress(stages, stageOrder),
    [stages, stageOrder],
  );
  const { ordered, completed, runningStage, progressPct, trackFillPct } = live;

  const [selectedStage, setSelectedStage] = useState<string | null>(null);
  const [pinned, setPinned] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const indexStagesShown = useMemo(
    () => visibleStages(ordered, expanded),
    [ordered, expanded],
  );
  const hiddenStageCount = useMemo(() => {
    const cutoff = ordered.findIndex((stage) => stage.stage === COLLAPSED_STAGE_UP_TO);
    if (cutoff === -1 || cutoff >= ordered.length - 1) return 0;
    return ordered.length - (cutoff + 1);
  }, [ordered]);
  const canExpandStages = hiddenStageCount > 0;
  const runningIndex =
    runningStage != null
      ? ordered.findIndex((stage) => stage.stage === runningStage.stage)
      : -1;

  const activeKey = selectedStage ?? defaultSelected(ordered)?.stage ?? null;
  const active = ordered.find((s) => s.stage === activeKey) ?? null;

  useEffect(() => {
    setPinned(false);
    setSelectedStage(null);
  }, [runningRunId]);

  useEffect(() => {
    if (pinned) return;
    if (isLive && runningStage) {
      setSelectedStage(runningStage.stage);
      return;
    }
    const pick = defaultSelected(ordered);
    if (pick) setSelectedStage(pick.stage);
  }, [ordered, pinned, isLive, runningStage]);

  return (
    <div className="jarvis-pipeline-stages">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-muted-foreground">
            {completed} of {ordered.length} stages complete
            {isLive && runningStage && (
              <span className="ml-2 text-[hsl(187_80%_65%)]">
                · live: {formatStageName(runningStage.stage)}
              </span>
            )}
          </p>
          {isLive && (
            <button
              type="button"
              onClick={() => setPinned(false)}
              className={`mt-1 font-mono text-[9px] uppercase tracking-wider ${
                pinned ? "text-[hsl(187_75%_60%)] hover:underline" : "text-muted-foreground/60"
              }`}
            >
              {pinned ? "Resume live sync" : "Following backend"}
            </button>
          )}
        </div>
        <div className="flex min-w-[160px] items-center gap-3">
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted/80">
            <motion.div
              className="jarvis-score-fill h-full rounded-full"
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: reduceMotion ? 0 : 0.5 }}
            />
          </div>
          <span className="font-mono text-xs text-[hsl(187_85%_72%)]">{progressPct}%</span>
        </div>
      </div>

      <div
        className="jarvis-stage-filmstrip relative mb-6 rounded-xl border border-[hsl(187_35%_28%/0.35)] bg-[hsl(187_22%_8%/0.35)] px-3 py-3 sm:px-5"
        style={
          {
            "--stage-count": ordered.length,
            "--track-fill": `${trackFillPct}%`,
          } as CSSProperties
        }
      >
        <div
          className="jarvis-filmstrip-grid relative"
          role="tablist"
          aria-label="Pipeline stages"
          data-dense={ordered.length > 10 ? "true" : undefined}
        >
          <div className="jarvis-filmstrip-track pointer-events-none absolute inset-x-0 top-[1.625rem] z-0 hidden h-px sm:block" />
          <div
            className="jarvis-filmstrip-track-fill pointer-events-none absolute top-[1.625rem] z-0 hidden h-0.5 sm:block"
            style={{
              left: "calc(50% / var(--stage-count))",
              width: "calc((100% - 100% / var(--stage-count)) * var(--track-fill) / 100)",
            }}
            aria-hidden
          />
          {ordered.map((stage, index) => {
            const isSelected = stage.stage === activeKey;
            const inProcess = stage.status === "running";
            const isDone =
              stage.status === "completed" ||
              stage.status === "failed" ||
              stage.status === "skipped";
            const labelMax = ordered.length > 10 ? 7 : 10;
            return (
              <button
                key={stage.stage}
                type="button"
                role="tab"
                aria-selected={isSelected}
                onClick={() => {
                  setSelectedStage(stage.stage);
                  setPinned(true);
                }}
                className="jarvis-filmstrip-node group relative z-10"
                aria-label={`${formatStageName(stage.stage)}, ${stage.status}`}
              >
                <span
                  className={`jarvis-stage-node relative mx-auto flex h-9 w-9 shrink-0 items-center justify-center rounded-full border font-mono text-[10px] font-semibold ${stageTone(stage.status)} ${
                    isSelected ? "jarvis-stage-node--focus" : ""
                  } ${inProcess ? "jarvis-stage-node--process" : ""} ${
                    isDone && !inProcess ? "jarvis-stage-node--synced" : ""
                  }`}
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
                  {stageShortLabel(stage.stage, labelMax)}
                </span>
              </button>
            );
          })}
        </div>

        {isLive && runningIndex >= 0 && !reduceMotion && (
          <motion.div
            className="jarvis-schematic-pulse pointer-events-none absolute top-[1.55rem] z-20 hidden h-1.5 w-6 rounded-full bg-[hsl(187_95%_62%)] sm:block"
            animate={{
              left: `calc((100% / ${ordered.length}) * ${runningIndex} + (100% / ${ordered.length}) / 2 - 12px)`,
            }}
            transition={{ type: "spring", stiffness: 120, damping: 20 }}
            aria-hidden
          />
        )}
      </div>

      {active ? (
        <StageDetailLens stage={active} reduceMotion={!!reduceMotion} isLive={inProcessStage(active)} />
      ) : (
        <p className="text-sm text-muted-foreground">No stage data available.</p>
      )}

      <ul className="mt-6 space-y-1 border-t border-border/50 pt-5" aria-label="Stage index">
        {indexStagesShown.map((stage) => {
          const isSelected = stage.stage === activeKey;
          return (
            <li key={stage.stage}>
              <button
                type="button"
                onClick={() => {
                  setSelectedStage(stage.stage);
                  setPinned(true);
                }}
                className={`jarvis-stage-index-row flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
                  isSelected ? "jarvis-stage-index-row--active" : ""
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

      {canExpandStages && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-lg border border-[hsl(187_35%_28%/0.4)] bg-[hsl(187_24%_10%/0.25)] py-2 font-mono text-[10px] uppercase tracking-wider text-[hsl(187_75%_60%)] transition-colors hover:border-[hsl(187_55%_45%/0.55)] hover:text-[hsl(187_85%_72%)]"
        >
          {expanded
            ? "Show fewer stages"
            : `Show remaining stages (${hiddenStageCount} more)`}
          <ChevronDown
            className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")}
            aria-hidden
          />
        </button>
      )}
    </div>
  );
}

function inProcessStage(stage: DashboardPipelineStageSummary): boolean {
  return stage.status === "running";
}

function StageDetailLens({
  stage,
  reduceMotion,
  isLive,
}: {
  stage: DashboardPipelineStageSummary;
  reduceMotion: boolean;
  isLive: boolean;
}) {
  const flow =
    stage.items_in > 0
      ? `${stage.items_in} in → ${stage.items_out} out`
      : `${stage.records_processed} processed`;

  const throughputPct =
    stage.items_in > 0
      ? Math.min(100, Math.round((stage.items_out / stage.items_in) * 100))
      : stage.status === "running"
        ? 35
        : stage.status === "completed"
          ? 100
          : 0;

  return (
    <motion.div
      key={stage.stage}
      className={`jarvis-stage-lens relative overflow-hidden rounded-2xl border bg-gradient-to-br from-[hsl(187_26%_11%/0.55)] to-transparent p-6 ${
        isLive
          ? "border-[hsl(187_55%_45%/0.65)] shadow-[0_0_32px_hsl(187_90%_50%/0.12)]"
          : "border-[hsl(187_40%_32%/0.45)]"
      }`}
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 24 }}
    >
      <div className="jarvis-hero-glow pointer-events-none absolute -right-20 -top-20 h-40 w-40 opacity-40" aria-hidden />

      <div className="relative flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
            {isLive ? "Live stage" : "Inspecting"}
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

      {isLive && (
        <div className="relative mt-4">
          <div className="mb-1 flex justify-between font-mono text-[10px] text-muted-foreground">
            <span>Stage progress</span>
            <span className="text-[hsl(187_85%_72%)]">executing…</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted/80">
            <motion.div
              className="jarvis-score-fill h-full rounded-full"
              animate={{ width: ["20%", "85%", "20%"] }}
              transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
            />
          </div>
        </div>
      )}

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

      {!isLive && throughputPct > 0 && (
        <div className="relative mt-4 h-1 overflow-hidden rounded-full bg-muted/70">
          <div className="jarvis-score-fill h-full rounded-full" style={{ width: `${throughputPct}%` }} />
        </div>
      )}
    </motion.div>
  );
}
