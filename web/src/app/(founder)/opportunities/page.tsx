"use client";

import { useMemo, useState } from "react";
import { LiveIndicator, PageHeader, ErrorState } from "@/components/layout/page-header";
import { DataTable, StatusBadge, type Column } from "@/components/shared/data-table";
import { Select } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import type {
  DashboardOpportunitiesResponse,
  DashboardOpportunityItem,
  OpportunityRead,
  PaginatedResponse,
} from "@/types/api";

const POLL_INTERVAL = 20_000;

export default function OpportunitiesPage() {
  const [reviewFilter, setReviewFilter] = useState("");
  const [source, setSource] = useState<"ranking" | "all">("ranking");

  const ranking = usePollingApi<DashboardOpportunitiesResponse>(
    `dashboard/opportunities${buildQuery({ top_n: 50 })}`,
    POLL_INTERVAL,
  );

  const listQuery = buildQuery({
    limit: 100,
    offset: 0,
    review_status: reviewFilter || undefined,
  });
  const all = usePollingApi<PaginatedResponse<OpportunityRead>>(
    source === "all" ? `opportunities${listQuery}` : null,
    POLL_INTERVAL,
  );

  const filteredRanking = useMemo(() => {
    const rows = ranking.data?.executive_rankings ?? [];
    if (!reviewFilter) return rows;
    return rows.filter((r) => r.review_status === reviewFilter);
  }, [ranking.data?.executive_rankings, reviewFilter]);

  const rankingColumns: Column<DashboardOpportunityItem>[] = [
    {
      key: "rank",
      header: "Rank",
      sortable: true,
      sortValue: (r) => r.rank ?? 999,
      render: (r) => r.rank ?? "—",
    },
    {
      key: "title",
      header: "Title",
      sortable: true,
      sortValue: (r) => r.title.toLowerCase(),
      render: (r) => r.title,
    },
    {
      key: "score",
      header: "Score",
      sortable: true,
      sortValue: (r) => r.final_opportunity_score ?? r.score ?? 0,
      render: (r) => r.final_opportunity_score ?? r.score ?? "—",
    },
    {
      key: "confidence",
      header: "Confidence",
      sortable: true,
      sortValue: (r) => r.confidence_score,
      render: (r) => `${Math.round(r.confidence_score * 100)}%`,
    },
    {
      key: "coverage",
      header: "Agents",
      sortable: true,
      sortValue: (r) => r.agent_coverage_count ?? 0,
      render: (r) => r.agent_coverage_count ?? "—",
    },
    {
      key: "status",
      header: "Review",
      sortable: true,
      sortValue: (r) => r.review_status,
      render: (r) => <StatusBadge status={r.review_status} />,
    },
  ];

  const allColumns: Column<OpportunityRead>[] = [
    {
      key: "title",
      header: "Title",
      sortable: true,
      sortValue: (r) => r.title.toLowerCase(),
      render: (r) => r.title,
    },
    {
      key: "confidence",
      header: "Confidence",
      sortable: true,
      sortValue: (r) => r.confidence_score,
      render: (r) => `${Math.round(r.confidence_score * 100)}%`,
    },
    {
      key: "status",
      header: "Review",
      sortable: true,
      sortValue: (r) => r.review_status,
      render: (r) => <StatusBadge status={r.review_status} />,
    },
    {
      key: "model",
      header: "Model",
      render: (r) => r.llm_model,
    },
  ];

  const active = source === "ranking" ? ranking : all;
  if (active.error) {
    return <ErrorState message={active.error.message} onRetry={() => active.mutate()} />;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Opportunities"
        description="Executive rankings and full opportunity inventory from the backend."
        onRefresh={() => {
          ranking.mutate();
          all.mutate();
        }}
        isRefreshing={ranking.isValidating || all.isValidating}
        actions={<LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Select value={source} onChange={(e) => setSource(e.target.value as "ranking" | "all")}>
          <option value="ranking">Executive ranking</option>
          <option value="all">All opportunities</option>
        </Select>
        <Select value={reviewFilter} onChange={(e) => setReviewFilter(e.target.value)}>
          <option value="">All review statuses</option>
          <option value="new">New</option>
          <option value="reviewing">Reviewing</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="archived">Archived</option>
        </Select>
      </div>

      {!active.data ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : source === "ranking" ? (
        <DataTable
          data={filteredRanking}
          columns={rankingColumns}
          rowKey={(r) => r.opportunity_id}
          filterFn={(r, q) => r.title.toLowerCase().includes(q)}
          filterPlaceholder="Filter by title…"
          emptyMessage="No ranked opportunities match your filters."
        />
      ) : (
        <DataTable
          data={all.data?.items ?? []}
          columns={allColumns}
          rowKey={(r) => r.id}
          filterFn={(r, q) => r.title.toLowerCase().includes(q)}
          filterPlaceholder="Filter by title…"
          emptyMessage="No opportunities match your filters."
        />
      )}
    </div>
  );
}
