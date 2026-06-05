"use client";

import { AgentStepRail } from "@/components/agents/agent-step-rail";
import type { AgentStepSync } from "@/lib/agents/agent-step-sync";

interface AgentPipelineSchematicProps {
  stepSync: AgentStepSync;
}

export function AgentPipelineSchematic({ stepSync }: AgentPipelineSchematicProps) {
  return (
    <div className="mb-10 hidden lg:block">
      <AgentStepRail
        sync={stepSync}
        variant="wide"
        showPhaseLabels
        title="Execution map · Discover → Validate → Strategize"
      />
    </div>
  );
}
