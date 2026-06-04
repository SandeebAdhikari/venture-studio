import { PipelineJarvisStages } from "@/components/pipeline/pipeline-jarvis-stages";
import type { DashboardPipelineStageSummary } from "@/types/api";

interface PipelineStagesProps {
  stages: DashboardPipelineStageSummary[];
  stageOrder: string[];
}

/** @deprecated Use PipelineJarvisStages — kept for imports that expect PipelineStages */
export function PipelineStages({ stages, stageOrder }: PipelineStagesProps) {
  return <PipelineJarvisStages stages={stages} stageOrder={stageOrder} />;
}
