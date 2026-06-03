"use client";

import { useState } from "react";
import { ReportViewer } from "@/components/reports/report-viewer";
import { LiveIndicator, PageHeader, ErrorState, EmptyState } from "@/components/layout/page-header";
import { DataTable, StatusBadge, type Column } from "@/components/shared/data-table";
import { Select } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi, useApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import { formatDate } from "@/lib/utils";
import type {
  DashboardReportSummary,
  DashboardReportsResponse,
  ReportMarkdownRead,
} from "@/types/api";

const POLL_INTERVAL = 30_000;

export default function ReportsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");

  const reports = usePollingApi<DashboardReportsResponse>(
    `dashboard/reports${buildQuery({ limit: 20 })}`,
    POLL_INTERVAL,
  );

  const markdown = useApi<ReportMarkdownRead>(
    selectedId ? `reports/${selectedId}/markdown` : null,
  );

  const allReports: DashboardReportSummary[] = reports.data
    ? [
        ...(reports.data.featured_venture_report ? [reports.data.featured_venture_report] : []),
        ...reports.data.venture_reports,
        ...reports.data.top_opportunity_reports,
        ...reports.data.pipeline_reports,
      ].filter(
        (report, index, arr) => arr.findIndex((r) => r.id === report.id) === index,
      )
    : [];

  const filtered = typeFilter
    ? allReports.filter((r) => r.report_type === typeFilter)
    : allReports;

  const columns: Column<DashboardReportSummary>[] = [
    {
      key: "title",
      header: "Title",
      sortable: true,
      sortValue: (r) => r.title.toLowerCase(),
      render: (r) => (
        <button
          type="button"
          className="text-left font-medium text-primary hover:underline"
          onClick={() => setSelectedId(r.id)}
        >
          {r.title}
        </button>
      ),
    },
    {
      key: "type",
      header: "Type",
      sortable: true,
      sortValue: (r) => r.report_type,
      render: (r) => r.report_type.replace(/_/g, " "),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      sortValue: (r) => r.status,
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "created",
      header: "Created",
      sortable: true,
      sortValue: (r) => r.created_at,
      render: (r) => formatDate(r.created_at),
    },
  ];

  if (reports.error) {
    return <ErrorState message={reports.error.message} onRetry={() => reports.mutate()} />;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Reports"
        description="Venture recommendations, top opportunities, and pipeline summaries."
        onRefresh={() => reports.mutate()}
        isRefreshing={reports.isValidating}
        actions={<LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />}
      />

      <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="max-w-xs">
        <option value="">All report types</option>
        <option value="venture_recommendation">Venture recommendation</option>
        <option value="top_opportunities">Top opportunities</option>
        <option value="pipeline_summary">Pipeline summary</option>
        <option value="opportunity_brief">Opportunity brief</option>
      </Select>

      {!reports.data ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Report library</CardTitle>
            </CardHeader>
            <CardContent>
              {filtered.length === 0 ? (
                <EmptyState title="No reports" description="Generate reports via the pipeline or API." />
              ) : (
                <DataTable
                  data={filtered}
                  columns={columns}
                  rowKey={(r) => r.id}
                  filterFn={(r, q) => r.title.toLowerCase().includes(q)}
                  filterPlaceholder="Search reports…"
                />
              )}
            </CardContent>
          </Card>

          <div>
            {selectedId ? (
              <ReportViewer
                title={markdown.data?.title ?? "Report"}
                markdown={markdown.data?.markdown}
                isLoading={markdown.isLoading}
              />
            ) : (
              <EmptyState
                title="Select a report"
                description="Click a report title to view its markdown content."
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
