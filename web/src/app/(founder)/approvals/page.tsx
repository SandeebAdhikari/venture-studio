"use client";

import { useState } from "react";
import { ApprovalActions } from "@/components/approvals/approval-actions";
import { LiveIndicator, PageHeader, ErrorState } from "@/components/layout/page-header";
import { DataTable, StatusBadge, type Column } from "@/components/shared/data-table";
import { Select } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import { formatDate } from "@/lib/utils";
import type { ApprovalRequestRead, PaginatedResponse } from "@/types/api";

const POLL_INTERVAL = 15_000;

export default function ApprovalsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const query = buildQuery({
    limit: 50,
    offset: 0,
    status: statusFilter || undefined,
    subject_type: subjectFilter || undefined,
  });

  const approvals = usePollingApi<PaginatedResponse<ApprovalRequestRead>>(
    `approvals${query}`,
    POLL_INTERVAL,
  );

  const items = approvals.data?.items ?? [];
  const selected = items.find((a) => a.id === selectedId) ?? items[0] ?? null;

  const columns: Column<ApprovalRequestRead>[] = [
    {
      key: "title",
      header: "Title",
      sortable: true,
      sortValue: (a) => a.title.toLowerCase(),
      render: (a) => (
        <button
          type="button"
          className={`text-left font-medium ${selected?.id === a.id ? "text-foreground underline" : "text-muted-foreground"}`}
          onClick={() => setSelectedId(a.id)}
        >
          {a.title}
        </button>
      ),
    },
    {
      key: "subject",
      header: "Subject",
      sortable: true,
      sortValue: (a) => a.subject_type,
      render: (a) => a.subject_type.replace(/_/g, " "),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      sortValue: (a) => a.status,
      render: (a) => <StatusBadge status={a.status} />,
    },
    {
      key: "updated",
      header: "Updated",
      sortable: true,
      sortValue: (a) => a.updated_at,
      render: (a) => formatDate(a.updated_at),
    },
  ];

  if (approvals.error) {
    return <ErrorState message={approvals.error.message} onRetry={() => approvals.mutate()} />;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Approvals"
        description="Review and action founder approval requests for rankings and venture reports."
        onRefresh={() => approvals.mutate()}
        isRefreshing={approvals.isValidating}
        actions={<LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />}
      />

      <div className="filter-panel">
        <p className="filter-panel-label mb-3">Filters</p>
        <div className="flex flex-col gap-3 sm:flex-row">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="max-w-xs">
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="research_requested">Research requested</option>
        </Select>
        <Select value={subjectFilter} onChange={(e) => setSubjectFilter(e.target.value)} className="max-w-xs">
          <option value="">All subjects</option>
          <option value="executive_ranking">Executive ranking</option>
          <option value="venture_report">Venture report</option>
        </Select>
        </div>
      </div>

      {!approvals.data ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle>Requests ({approvals.data.total})</CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                data={items}
                columns={columns}
                rowKey={(a) => a.id}
                filterFn={(a, q) => a.title.toLowerCase().includes(q)}
                filterPlaceholder="Filter by title…"
                emptyMessage="No approval requests match your filters."
              />
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Detail</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {selected ? (
                <>
                  <div>
                    <p className="font-medium">{selected.title}</p>
                    <div className="mt-2 flex gap-2">
                      <StatusBadge status={selected.status} />
                      <StatusBadge status={selected.subject_type} />
                    </div>
                  </div>
                  <ApprovalActions approval={selected} onComplete={() => approvals.mutate()} />
                  {selected.decisions.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium">Comment history</p>
                      {selected.decisions.map((d) => (
                        <div key={d.id} className="rounded-lg border border-border p-3 text-sm">
                          <p className="font-medium">{d.decision_type.replace(/_/g, " ")}</p>
                          {d.comment && (
                            <p className="mt-1 text-muted-foreground">{d.comment}</p>
                          )}
                          <p className="mt-1 text-xs text-muted-foreground">
                            {d.actor} · {formatDate(d.created_at)}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Select an approval request.</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
