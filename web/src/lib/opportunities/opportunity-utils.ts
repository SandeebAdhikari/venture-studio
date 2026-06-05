import type { DashboardOpportunityItem } from "@/types/api";

export function opportunityScore(item: DashboardOpportunityItem): number | null {
  const raw = item.final_opportunity_score ?? item.score;
  return raw != null ? Number(raw) : null;
}

export function scorePercent(score: number | null): number {
  if (score == null) return 0;
  return Math.min(100, Math.max(0, score));
}

export function opportunityDimensions(item: DashboardOpportunityItem) {
  const dims = [
    { key: "pain", label: "Pain", value: item.pain_score },
    { key: "market", label: "Market", value: item.market_score },
    { key: "revenue", label: "Revenue", value: item.revenue_score },
    { key: "competition", label: "Competition", value: item.competition_score },
    { key: "growth", label: "Growth", value: item.growth_score },
    { key: "founder", label: "Founder fit", value: item.founder_fit_score },
  ];
  return dims.filter((d) => d.value != null) as Array<{
    key: string;
    label: string;
    value: number;
  }>;
}
