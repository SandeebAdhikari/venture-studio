import type { DashboardPipelineStageSummary } from "@/types/api";

export function orderPipelineStages(
  stages: DashboardPipelineStageSummary[],
  stageOrder: string[],
): DashboardPipelineStageSummary[] {
  const byStage = new Map(stages.map((s) => [s.stage, s]));
  if (stageOrder.length) {
    return stageOrder
      .map((name) => byStage.get(name))
      .filter(Boolean) as DashboardPipelineStageSummary[];
  }
  return [...stages].sort((a, b) => a.sequence - b.sequence);
}

export function formatStageName(stage: string): string {
  return stage.replace(/_/g, " ");
}

export function stageShortLabel(stage: string, maxLen = 12): string {
  const parts = stage.split("_").filter(Boolean);
  let label: string;
  if (parts.length === 0) label = stage;
  else if (parts.length === 1) label = parts[0];
  else {
    const two = `${parts[0]} ${parts[1]}`;
    label = two.length > maxLen ? parts[0] : two;
  }
  if (label.length <= maxLen) return label;
  return `${label.slice(0, Math.max(1, maxLen - 1))}…`;
}
