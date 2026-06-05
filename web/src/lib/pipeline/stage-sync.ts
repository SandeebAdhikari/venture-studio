import type { DashboardPipelineStageSummary, PipelineStageStatus } from "@/types/api";
import { orderPipelineStages } from "@/lib/pipeline/stage-order";

/** Pipeline stages that map 1:1 to research agent keys in the dashboard API. */
export const STAGE_TO_AGENT_KEY: Record<string, string> = {
  market_research: "market_research",
  competitor_analysis: "competitor_analysis",
  customer_research: "customer_research",
  revenue_validation: "revenue_validation",
  product_strategy: "product_strategy",
  go_to_market: "go_to_market",
  growth_strategy: "growth_strategy",
  human_proxy: "human_proxy",
};

export function agentKeyForStage(stage: string): string | null {
  return STAGE_TO_AGENT_KEY[stage] ?? null;
}

export function truncateText(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return `${text.slice(0, Math.max(1, maxLen - 1)).trimEnd()}…`;
}

export interface PipelineLiveProgress {
  ordered: DashboardPipelineStageSummary[];
  completed: number;
  runningIndex: number;
  runningStage: DashboardPipelineStageSummary | null;
  progressPct: number;
  trackFillPct: number;
}

export function computePipelineLiveProgress(
  stages: DashboardPipelineStageSummary[],
  stageOrder: string[],
): PipelineLiveProgress {
  const ordered = orderPipelineStages(stages, stageOrder);
  const total = ordered.length || 1;
  const completed = ordered.filter((s) => s.status === "completed").length;
  const runningIndex = ordered.findIndex((s) => s.status === "running");
  const runningStage = runningIndex >= 0 ? ordered[runningIndex] : null;

  const terminal = ordered.filter(
    (s) => s.status === "completed" || s.status === "failed" || s.status === "skipped",
  ).length;

  let progressPct = Math.round((completed / total) * 100);
  if (runningStage) {
    progressPct = Math.round(((runningIndex + 0.35) / total) * 100);
  } else if (terminal === total) {
    progressPct = 100;
  }

  const trackFillPct =
    runningIndex >= 0
      ? ((runningIndex + 0.5) / total) * 100
      : completed > 0
        ? (completed / total) * 100
        : 0;

  return {
    ordered,
    completed,
    runningIndex,
    runningStage,
    progressPct: Math.min(100, Math.max(0, progressPct)),
    trackFillPct: Math.min(100, Math.max(0, trackFillPct)),
  };
}

export function stageTone(status: PipelineStageStatus): string {
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
