import { Badge, statusVariant } from "@/components/ui/badge";
import { formatDuration } from "@/lib/utils";
import type { DashboardPipelineStageSummary } from "@/types/api";

interface PipelineStagesProps {
  stages: DashboardPipelineStageSummary[];
  stageOrder: string[];
}

export function PipelineStages({ stages, stageOrder }: PipelineStagesProps) {
  const byStage = new Map(stages.map((s) => [s.stage, s]));
  const ordered = stageOrder.length
    ? stageOrder.map((name) => byStage.get(name)).filter(Boolean) as DashboardPipelineStageSummary[]
    : [...stages].sort((a, b) => a.sequence - b.sequence);

  return (
    <div className="space-y-2">
      {ordered.map((stage) => (
        <div
          key={`${stage.stage}-${stage.sequence}`}
          className="flex flex-col gap-2 rounded-lg border border-border p-4 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-medium">{stage.stage.replace(/_/g, " ")}</p>
              <Badge variant={statusVariant(stage.status)}>{stage.status}</Badge>
            </div>
            {stage.error_detail && (
              <p className="mt-1 truncate text-xs text-destructive">{stage.error_detail}</p>
            )}
          </div>
          <div className="flex shrink-0 flex-wrap gap-4 text-xs text-muted-foreground">
            <span>In: {stage.items_in}</span>
            <span>Out: {stage.items_out}</span>
            <span>Failed: {stage.items_failed}</span>
            <span>{formatDuration(stage.duration_ms)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
