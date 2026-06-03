"use client";

import { useState } from "react";
import { PipelineStages } from "@/components/pipeline/pipeline-stages";
import { LiveIndicator, PageHeader, ErrorState } from "@/components/layout/page-header";
import { DataTable, StatusBadge, type Column } from "@/components/shared/data-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import { formatDate, formatDuration } from "@/lib/utils";
import type { DashboardPipelineResponse, DashboardPipelineRunSummary } from "@/types/api";

const POLL_INTERVAL = 10_000;

export default function PipelinePage() {
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const pipeline = usePollingApi<DashboardPipelineResponse>(
    `dashboard/pipeline${buildQuery({ limit, offset, include_stages: true })}`,
    POLL_INTERVAL,
  );

  const columns: Column<DashboardPipelineRunSummary>[] = [
    {
      key: "status",
      header: "Status",
      sortable: true,
      sortValue: (r) => r.status,
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "trigger",
      header: "Trigger",
      sortable: true,
      sortValue: (r) => r.trigger,
      render: (r) => r.trigger,
    },
    {
      key: "started",
      header: "Started",
      sortable: true,
      sortValue: (r) => r.started_at ?? "",
      render: (r) => formatDate(r.started_at),
    },
    {
      key: "duration",
      header: "Duration",
      sortable: true,
      sortValue: (r) => r.duration_ms ?? 0,
      render: (r) => formatDuration(r.duration_ms),
    },
    {
      key: "stages",
      header: "Stages",
      render: (r) => (
        <span className="text-xs text-muted-foreground">
          {r.stages_completed} ok · {r.stages_failed} failed · {r.stages_skipped} skipped
        </span>
      ),
    },
  ];

  if (pipeline.error) {
    return <ErrorState message={pipeline.error.message} onRetry={() => pipeline.mutate()} />;
  }

  const runs = pipeline.data?.runs.items ?? [];
  const total = pipeline.data?.runs.total ?? 0;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Pipeline"
        description="Monitor pipeline runs and stage-level execution from the backend orchestrator."
        onRefresh={() => pipeline.mutate()}
        isRefreshing={pipeline.isValidating}
        actions={<LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />}
      />

      {!pipeline.data ? (
        <Skeleton className="h-96 w-full rounded-xl" />
      ) : (
        <>
          {pipeline.data.running && (
            <Card className="border-primary/30">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Active run
                  <StatusBadge status={pipeline.data.running.status} />
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Started {formatDate(pipeline.data.running.started_at)}
              </CardContent>
            </Card>
          )}

          {pipeline.data.latest_detail && (
            <Card>
              <CardHeader>
                <CardTitle>Latest run stages</CardTitle>
              </CardHeader>
              <CardContent>
                <PipelineStages
                  stages={pipeline.data.latest_detail.stage_runs}
                  stageOrder={pipeline.data.stage_order}
                />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Run history ({total})</CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                data={runs}
                columns={columns}
                rowKey={(r) => r.id}
                emptyMessage="No pipeline runs recorded."
              />
              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  className="text-sm text-primary disabled:opacity-40"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="text-sm text-primary disabled:opacity-40"
                  disabled={offset + limit >= total}
                  onClick={() => setOffset(offset + limit)}
                >
                  Next
                </button>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
