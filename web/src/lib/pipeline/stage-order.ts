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

export function stageShortLabel(stage: string): string {
  const parts = stage.split("_").filter(Boolean);
  if (parts.length === 0) return stage;
  if (parts.length === 1) return parts[0];
  const two = `${parts[0]} ${parts[1]}`;
  return two.length > 14 ? parts[0] : two;
}
