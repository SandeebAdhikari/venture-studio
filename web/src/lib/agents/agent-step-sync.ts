import type { DashboardAgentStatus, DashboardPipelineStageSummary } from "@/types/api";
import {
  RESEARCH_AGENT_PIPELINE,
  sortAgentsByPipeline,
} from "@/lib/agents/pipeline-order";
import { orderPipelineStages } from "@/lib/pipeline/stage-order";
import { agentKeyForStage } from "@/lib/pipeline/stage-sync";

export type AgentStepState = "pending" | "running" | "completed" | "failed" | "skipped";

export interface AgentStepSync {
  steps: Record<number, AgentStepState>;
  activeStep: number | null;
  completedCount: number;
  isLive: boolean;
}

const AGENT_KEY_TO_STEP = new Map(
  RESEARCH_AGENT_PIPELINE.map((item, i) => [item.key, i + 1]),
);

function mapStageStatus(status: DashboardPipelineStageSummary["status"]): AgentStepState {
  if (status === "completed") return "completed";
  if (status === "running") return "running";
  if (status === "failed") return "failed";
  if (status === "skipped") return "skipped";
  return "pending";
}

function syncFromPipeline(
  stages: DashboardPipelineStageSummary[],
  stageOrder: string[],
): AgentStepSync {
  const ordered = orderPipelineStages(stages, stageOrder);
  const byStage = new Map(ordered.map((s) => [s.stage, s.status]));
  const steps: Record<number, AgentStepState> = {};
  let activeStep: number | null = null;

  RESEARCH_AGENT_PIPELINE.forEach((item, i) => {
    const step = i + 1;
    const status = byStage.get(item.key);
    steps[step] = status ? mapStageStatus(status) : "pending";
    if (steps[step] === "running") activeStep = step;
  });

  const completedCount = Object.values(steps).filter((s) => s === "completed").length;

  return { steps, activeStep, completedCount, isLive: activeStep != null };
}

function syncFromAgents(agents: DashboardAgentStatus[]): AgentStepSync {
  const steps: Record<number, AgentStepState> = {};
  for (let i = 1; i <= 8; i += 1) steps[i] = "pending";

  sortAgentsByPipeline(agents).forEach((agent) => {
    if (agent.step < 1 || agent.step > 8) return;
    if (agent.current_failed > 0) {
      steps[agent.step] = "failed";
    } else if (agent.current_total > 0 && agent.current_completed >= agent.current_total) {
      steps[agent.step] = "completed";
    } else if (agent.current_completed > 0) {
      steps[agent.step] = "completed";
    }
  });

  const completedCount = Object.values(steps).filter((s) => s === "completed").length;
  return { steps, activeStep: null, completedCount, isLive: false };
}

export function computeAgentStepSync(
  stages: DashboardPipelineStageSummary[] | undefined,
  stageOrder: string[],
  agents: DashboardAgentStatus[],
  isPipelineLive: boolean,
  activeAgentKey: string | null,
): AgentStepSync {
  const hasPipelineStages = (stages?.length ?? 0) > 0 && stageOrder.length > 0;
  const sync =
    isPipelineLive && hasPipelineStages
      ? syncFromPipeline(stages!, stageOrder)
      : syncFromAgents(agents);

  if (activeAgentKey) {
    const step = AGENT_KEY_TO_STEP.get(activeAgentKey) ?? null;
    if (step != null) {
      sync.activeStep = step;
      if (sync.steps[step] === "pending") sync.steps[step] = "running";
    }
  }

  if (isPipelineLive) {
    sync.isLive = true;
  }

  return sync;
}

export function stepForAgentKey(agentKey: string | null): number | null {
  if (!agentKey) return null;
  return AGENT_KEY_TO_STEP.get(agentKey) ?? null;
}

export function agentKeyForStep(step: number): string | null {
  return RESEARCH_AGENT_PIPELINE[step - 1]?.key ?? null;
}

/** Re-export for stage → agent lookups used elsewhere */
export { agentKeyForStage };
