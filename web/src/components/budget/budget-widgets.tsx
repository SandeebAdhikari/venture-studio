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
      indicatorClassName={budgetExceeded ? "bg-muted-foreground" : undefined}
    />
  );
}

export function BudgetWarningsList({ warnings }: { warnings: BudgetWarning[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {warnings.map((w) => (
        <span
          key={w.threshold_pct}
          className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${
            w.triggered
              ? "border-foreground/30 bg-foreground text-background"
              : "border-border bg-muted text-muted-foreground"
          }`}
        >
          {w.threshold_pct}% {w.triggered ? "triggered" : "ok"}
        </span>
      ))}
    </div>
  );
}

export function AgentUsageTable({ agents }: { agents: BudgetAgentUsage[] }) {
  if (agents.length === 0) {
    return <p className="text-sm text-muted-foreground">No agent usage recorded today.</p>;
  }
  return (
    <div className="data-table-wrap overflow-x-auto">
      <table className="data-table w-full min-w-[520px] text-sm">
        <thead>
          <tr>
            <th className="px-4 py-3 text-left font-medium">Agent</th>
            <th className="px-4 py-3 text-right font-medium">Calls</th>
            <th className="px-4 py-3 text-right font-medium">Actual</th>
            <th className="px-4 py-3 text-right font-medium">Estimated</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((agent) => (
            <tr key={agent.graph_name} className="border-t border-border">
              <td className="px-4 py-3">{agent.display_name}</td>
              <td className="px-4 py-3 text-right">{agent.calls_total}</td>
              <td className="px-4 py-3 text-right">{formatUsd(agent.actual_cost_usd_total, 4)}</td>
              <td className="px-4 py-3 text-right">{formatUsd(agent.estimated_cost_usd_total, 4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BudgetHistoryChart({ items }: { items: BudgetHistoryDay[] }) {
  const max = Math.max(...items.map((i) => i.spent_usd), 0.0001);
  return (
    <div className="flex h-40 items-end gap-2">
      {[...items].reverse().slice(-14).map((day) => {
        const height = Math.max((day.spent_usd / max) * 100, 4);
        return (
          <div key={day.usage_date} className="flex flex-1 flex-col items-center gap-1">
            <div
              className={`w-full rounded-t ${day.budget_exceeded ? "bg-muted-foreground" : "bg-foreground/80"}`}
              style={{ height: `${height}%` }}
              title={`${day.usage_date}: ${formatUsd(day.spent_usd, 4)}`}
            />
            <span className="text-[10px] text-muted-foreground">
              {new Date(day.usage_date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
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
