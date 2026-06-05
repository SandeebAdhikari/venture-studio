import { Progress } from "@/components/ui/progress";
import { formatPercent, formatUsd } from "@/lib/utils";
import type { BudgetAgentUsage, BudgetHistoryDay, BudgetWarning } from "@/types/api";

export function BudgetUtilizationBar({
  utilizationPct,
  budgetExceeded,
}: {
  utilizationPct: number;
  budgetExceeded: boolean;
}) {
  const capped = Math.min(utilizationPct, 100);
  return (
    <Progress
      value={capped}
      indicatorClassName={
        budgetExceeded ? "bg-destructive" : "jarvis-score-fill !bg-[hsl(187_85%_55%)]"
      }
    />
  );
}

export function BudgetWarningsList({ warnings }: { warnings: BudgetWarning[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {warnings.map((w) => (
        <span
          key={w.threshold_pct}
          className={`rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${
            w.triggered
              ? "jarvis-status-pill jarvis-status-pill--active"
              : "border-[hsl(187_35%_28%/0.4)] bg-muted/30 text-muted-foreground"
          }`}
        >
          {w.threshold_pct}% {w.triggered ? "triggered" : "ok"}
        </span>
      ))}
    </div>
  );
}

export function AgentUsageTable({ agents }: { agents: BudgetAgentUsage[] }) {
  const maxCost = Math.max(...agents.map((a) => a.actual_cost_usd_total), 0.0001);
  return <BudgetAgentUsageList agents={agents} maxCost={maxCost} />;
}

export function BudgetAgentUsageList({
  agents,
  maxCost,
}: {
  agents: BudgetAgentUsage[];
  maxCost: number;
}) {
  if (agents.length === 0) {
    return <p className="text-sm text-muted-foreground">No agent usage recorded today.</p>;
  }

  const sorted = [...agents].sort((a, b) => b.actual_cost_usd_total - a.actual_cost_usd_total);

  return (
    <ul className="space-y-3">
      {sorted.map((agent) => {
        const pct = Math.round((agent.actual_cost_usd_total / maxCost) * 100);
        return (
          <li
            key={agent.graph_name}
            className="rounded-xl border border-[hsl(187_30%_26%/0.4)] bg-[hsl(187_24%_10%/0.3)] px-4 py-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-foreground">{agent.display_name}</p>
              <div className="flex gap-3 font-mono text-xs text-muted-foreground">
                <span>{agent.calls_total} calls</span>
                <span className="text-[hsl(187_85%_72%)]">
                  {formatUsd(agent.actual_cost_usd_total, 4)}
                </span>
              </div>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted/70">
              <div className="jarvis-score-fill h-full rounded-full" style={{ width: `${pct}%` }} />
            </div>
            <p className="mt-1 font-mono text-[10px] text-muted-foreground">
              Est. {formatUsd(agent.estimated_cost_usd_total, 4)}
            </p>
          </li>
        );
      })}
    </ul>
  );
}

export function BudgetHistoryChart({ items }: { items: BudgetHistoryDay[] }) {
  const max = Math.max(...items.map((i) => i.spent_usd), 0.0001);
  const days = [...items].reverse().slice(-14);

  return (
    <div className="budget-history-chart flex h-52 items-end gap-1.5 sm:gap-2">
      {days.map((day) => {
        const height = Math.max((day.spent_usd / max) * 100, 6);
        const util = Math.min(day.utilization_pct, 100);
        return (
          <div
            key={day.usage_date}
            className="group flex min-w-0 flex-1 flex-col items-center gap-2"
          >
            <div className="relative flex h-40 w-full items-end justify-center">
              <div
                className={`budget-history-bar w-full max-w-[2.5rem] rounded-t-md transition-opacity group-hover:opacity-90 ${
                  day.budget_exceeded ? "bg-destructive/85" : "jarvis-score-fill"
                }`}
                style={{ height: `${height}%` }}
                title={`${day.usage_date}: ${formatUsd(day.spent_usd, 4)} (${util.toFixed(0)}%)`}
              />
            </div>
            <span className="font-mono text-[9px] uppercase text-muted-foreground">
              {new Date(day.usage_date).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function BudgetSummaryLine({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

export { formatPercent, formatUsd };
