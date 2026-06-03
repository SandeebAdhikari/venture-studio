"use client";

import {
  AgentUsageTable,
  BudgetHistoryChart,
  BudgetSummaryLine,
  BudgetUtilizationBar,
  BudgetWarningsList,
  formatPercent,
  formatUsd,
} from "@/components/budget/budget-widgets";
import { LiveIndicator, PageHeader, ErrorState } from "@/components/layout/page-header";
import { MetricCard } from "@/components/shared/metric-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import type { BudgetHistoryResponse, BudgetStatusResponse } from "@/types/api";

const POLL_INTERVAL = 30_000;

export default function BudgetPage() {
  const status = usePollingApi<BudgetStatusResponse>("budget", POLL_INTERVAL);
  const history = usePollingApi<BudgetHistoryResponse>(
    `budget/history${buildQuery({ days: 30 })}`,
    POLL_INTERVAL,
  );

  if (status.error) {
    return <ErrorState message={status.error.message} onRetry={() => status.mutate()} />;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Budget"
        description="Daily LLM spend, per-agent usage, and threshold warnings from the backend."
        lastUpdated={history.data?.generated_at}
        onRefresh={() => {
          status.mutate();
          history.mutate();
        }}
        isRefreshing={status.isValidating || history.isValidating}
        actions={<LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />}
      />

      {!status.data ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Daily budget" value={formatUsd(status.data.budget_usd)} />
            <MetricCard title="Spent today" value={formatUsd(status.data.spent_usd, 4)} />
            <MetricCard title="Remaining" value={formatUsd(status.data.remaining_usd, 4)} />
            <MetricCard
              title="Utilization"
              value={formatPercent(status.data.utilization_pct)}
              subtitle={`${status.data.calls_total} LLM calls`}
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Daily utilization</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <BudgetUtilizationBar
                utilizationPct={status.data.utilization_pct}
                budgetExceeded={status.data.budget_exceeded}
              />
              <BudgetWarningsList warnings={status.data.warnings} />
              <div className="grid gap-2 sm:grid-cols-2">
                <BudgetSummaryLine
                  label="Prompt tokens"
                  value={status.data.prompt_tokens_total.toLocaleString()}
                />
                <BudgetSummaryLine
                  label="Completion tokens"
                  value={status.data.completion_tokens_total.toLocaleString()}
                />
                <BudgetSummaryLine
                  label="Estimated cost"
                  value={formatUsd(status.data.estimated_cost_usd_total, 4)}
                />
                <BudgetSummaryLine
                  label="Actual cost"
                  value={formatUsd(status.data.spent_usd, 4)}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Per-agent usage (today)</CardTitle>
            </CardHeader>
            <CardContent>
              <AgentUsageTable agents={status.data.by_agent} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>30-day history</CardTitle>
            </CardHeader>
            <CardContent>
              {!history.data ? (
                <Skeleton className="h-40 w-full" />
              ) : history.data.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">No historical usage yet.</p>
              ) : (
                <BudgetHistoryChart items={history.data.items} />
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
