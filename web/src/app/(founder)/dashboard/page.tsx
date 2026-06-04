"use client";

import Link from "next/link";
import { AgentCompactList } from "@/components/agents/agent-activity-grid";
import { useDashboardSession } from "@/components/layout/session-provider";
import { LiveIndicator, PageHeader, ErrorState } from "@/components/layout/page-header";
import { canAccessPage } from "@/lib/auth/rbac";
import { MetricCard } from "@/components/shared/metric-card";
import { StatusBadge } from "@/components/shared/data-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton, TableSkeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import { formatDate, formatUsd } from "@/lib/utils";
import type { DashboardOpportunitiesResponse, DashboardSummaryResponse } from "@/types/api";

const POLL_INTERVAL = 15_000;

export default function DashboardPage() {
  const session = useDashboardSession();
  const summary = usePollingApi<DashboardSummaryResponse>("dashboard/summary", POLL_INTERVAL);
  const canViewAgents = !session || canAccessPage("/agents", session.role);
  const opportunities = usePollingApi<DashboardOpportunitiesResponse>(
    `dashboard/opportunities${buildQuery({ top_n: 5 })}`,
    POLL_INTERVAL,
  );

  if (summary.error) {
    return (
      <ErrorState message={summary.error.message} onRetry={() => summary.mutate()} />
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="Venture studio overview — metrics, rankings, and background activity."
        lastUpdated={summary.data?.generated_at}
        onRefresh={() => summary.mutate()}
        isRefreshing={summary.isValidating}
        actions={<LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />}
      />

      {!summary.data ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Opportunities"
              value={summary.data.opportunities.total}
              subtitle={`${summary.data.research.opportunities_total} in research pipeline`}
            />
            <MetricCard
              title="Complaints classified"
              value={summary.data.classification.signals_classified}
              subtitle={`${summary.data.collection.signals_pending} pending signals`}
            />
            <MetricCard
              title="LLM spend today"
              value={formatUsd(summary.data.classification.llm_cost_usd_total, 4)}
              subtitle={`${summary.data.classification.llm_calls_total} calls`}
            />
            <MetricCard
              title="Ranked opportunities"
              value={summary.data.ranking.ranked_opportunity_count}
              subtitle={
                summary.data.ranking.version != null
                  ? `Ranking v${summary.data.ranking.version}`
                  : "No ranking yet"
              }
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Pipeline status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {summary.data.pipeline.running ? (
                  <div className="rounded-lg border border-border bg-muted/20 p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Running</span>
                      <StatusBadge status={summary.data.pipeline.running.status} />
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Started {formatDate(summary.data.pipeline.running.started_at)}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No pipeline run in progress.</p>
                )}
                {summary.data.pipeline.latest && (
                  <div className="rounded-lg bg-muted/30 p-4 text-sm">
                    <p className="font-medium">Latest run</p>
                    <p className="mt-1 text-muted-foreground">
                      {summary.data.pipeline.latest.stages_completed} completed ·{" "}
                      {summary.data.pipeline.latest.stages_failed} failed
                    </p>
                  </div>
                )}
                <Link href="/pipeline" className="app-link text-sm">
                  View pipeline →
                </Link>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Agent activity</CardTitle>
              </CardHeader>
              <CardContent>
                <AgentCompactList agents={(summary.data.agents ?? []).slice(0, 6)} />
                {canViewAgents && (
                  <Link href="/agents" className="app-link mt-4 inline-block text-sm">
                    View all agents →
                  </Link>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Top opportunities</CardTitle>
            </CardHeader>
            <CardContent>
              {!opportunities.data ? (
                <TableSkeleton rows={5} cols={4} />
              ) : opportunities.data.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">No ranked opportunities yet.</p>
              ) : (
                <div className="data-table-wrap overflow-x-auto">
                  <table className="data-table w-full text-sm">
                    <thead>
                      <tr className="text-left text-muted-foreground">
                        <th className="pb-2 pr-4">Rank</th>
                        <th className="pb-2 pr-4">Title</th>
                        <th className="pb-2 pr-4">Score</th>
                        <th className="pb-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {opportunities.data.items.map((item) => (
                        <tr key={item.opportunity_id} className="border-t border-border">
                          <td className="py-2 pr-4">{item.rank ?? "—"}</td>
                          <td className="py-2 pr-4 font-medium">{item.title}</td>
                          <td className="py-2 pr-4">
                            {item.final_opportunity_score ?? item.score ?? "—"}
                          </td>
                          <td className="py-2">
                            <StatusBadge status={item.review_status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
