"use client";

import { AgentActivityGrid } from "@/components/agents/agent-activity-grid";
import { LiveIndicator, PageHeader, ErrorState } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import type { DashboardSummaryResponse } from "@/types/api";

const POLL_INTERVAL = 20_000;

export default function AgentsPage() {
  const summary = usePollingApi<DashboardSummaryResponse>("dashboard/summary", POLL_INTERVAL);

  if (summary.error) {
    return <ErrorState message={summary.error.message} onRetry={() => summary.mutate()} />;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Agent Activity"
        description="Research agent completion metrics from the backend dashboard API."
        lastUpdated={summary.data?.generated_at}
        onRefresh={() => summary.mutate()}
        isRefreshing={summary.isValidating}
        actions={<LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />}
      />

      {!summary.data ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Coverage overview</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Average agent coverage across opportunities:{" "}
              <span className="font-medium text-foreground">
                {summary.data.research.average_agent_coverage != null
                  ? `${Math.round(summary.data.research.average_agent_coverage * 100) / 100}`
                  : "—"}
              </span>
            </CardContent>
          </Card>

          <AgentActivityGrid agents={summary.data.agents} />
        </>
      )}
    </div>
  );
}
