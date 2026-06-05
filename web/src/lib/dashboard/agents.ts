"use client";

import { sortAgentsByPipeline } from "@/lib/agents/pipeline-order";
import type { DashboardAgentStatus, DashboardSummaryResponse } from "@/types/api";

/** Prefer top-level agents from summary; fall back to nested research metrics. */
export function resolveDashboardAgents(summary: DashboardSummaryResponse): DashboardAgentStatus[] {
  const raw =
    summary.agents.length > 0 ? summary.agents : (summary.research?.agents ?? []);
  return sortAgentsByPipeline(raw);
}
