import type { DashboardAgentStatus } from "@/types/api";

/** Matches venture pipeline research stages (api/app/repositories/dashboard.py). */
export const RESEARCH_AGENT_PIPELINE: readonly { key: string; label: string }[] = [
  { key: "market_research", label: "Market Research" },
  { key: "competitor_analysis", label: "Competitor Analysis" },
  { key: "customer_research", label: "Customer Research" },
  { key: "revenue_validation", label: "Revenue Validation" },
  { key: "product_strategy", label: "Product Strategy" },
  { key: "go_to_market", label: "Go-To-Market" },
  { key: "growth_strategy", label: "Growth Strategy" },
  { key: "human_proxy", label: "Human Proxy" },
];

export const PIPELINE_PHASES = [
  {
    id: "discover",
    title: "Discover",
    subtitle: "Map the market landscape",
    stepRange: [1, 2] as const,
  },
  {
    id: "validate",
    title: "Validate",
    subtitle: "Test customer & revenue fit",
    stepRange: [3, 4] as const,
  },
  {
    id: "strategize",
    title: "Strategize",
    subtitle: "Synthesize venture direction",
    stepRange: [5, 8] as const,
  },
] as const;

const stepByKey = new Map(RESEARCH_AGENT_PIPELINE.map((item, i) => [item.key, i + 1]));

export type PipelineAgent = DashboardAgentStatus & { step: number };

export function sortAgentsByPipeline(agents: DashboardAgentStatus[]): PipelineAgent[] {
  return [...agents]
    .map((agent) => ({
      ...agent,
      step: stepByKey.get(agent.agent) ?? 99,
    }))
    .sort((a, b) => a.step - b.step);
}

export function agentsForPhase(
  sorted: PipelineAgent[],
  stepRange: readonly [number, number],
): PipelineAgent[] {
  const [min, max] = stepRange;
  return sorted.filter((a) => a.step >= min && a.step <= max);
}
