"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ReportsJarvisHero } from "@/components/reports/reports-jarvis-hero";
import { ReportsJarvisLibrary } from "@/components/reports/reports-jarvis-library";
import { ReportsJarvisViewer } from "@/components/reports/reports-jarvis-viewer";
import { LiveIndicator, ErrorState } from "@/components/layout/page-header";
import { flattenReports } from "@/lib/reports/report-utils";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi, useApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import type { DashboardReportsResponse, ReportMarkdownRead } from "@/types/api";

const POLL_INTERVAL = 30_000;

const BOOT_SEQUENCE = [
  "Indexing report archive…",
  "Loading venture summaries…",
  "Preparing markdown renderer…",
  "Reports console online.",
];

export default function ReportsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");
  const reduceMotion = useReducedMotion();
  const [bootLine, setBootLine] = useState(0);

  const reports = usePollingApi<DashboardReportsResponse>(
    `dashboard/reports${buildQuery({ limit: 20 })}`,
    POLL_INTERVAL,
  );

  const markdown = useApi<ReportMarkdownRead>(
    selectedId ? `reports/${selectedId}/markdown` : null,
  );

  const allReports = useMemo(
    () => (reports.data ? flattenReports(reports.data) : []),
    [reports.data],
  );

  useEffect(() => {
    if (reduceMotion) return;
    const id = setInterval(() => {
      setBootLine((n) => (n + 1) % BOOT_SEQUENCE.length);
    }, 2500);
    return () => clearInterval(id);
  }, [reduceMotion]);

  if (reports.error) {
    return (
      <div className="jarvis-page space-y-8">
        <ErrorState message={reports.error.message} onRetry={() => reports.mutate()} />
      </div>
    );
  }

  return (
    <div className="jarvis-page space-y-8">
      <div className="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <motion.p
            className="font-mono text-[10px] uppercase tracking-[0.4em] text-[hsl(187_75%_58%)]"
            animate={reduceMotion ? undefined : { opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            Intelligence archive
          </motion.p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground">Reports</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Venture recommendations, top opportunities, and pipeline summaries.
          </p>
          {!reduceMotion && (
            <p className="mt-2 font-mono text-xs text-[hsl(187_60%_50%)]">
              &gt; {BOOT_SEQUENCE[bootLine]}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => reports.mutate()}
            disabled={reports.isValidating}
            className="inline-flex h-8 items-center justify-center rounded-lg border border-border bg-card px-3 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            Refresh
          </button>
          <LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />
        </div>
      </div>

      {!reports.data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      ) : (
        <>
          <ReportsJarvisHero data={reports.data} libraryCount={allReports.length} />

          <div className="grid gap-6 lg:grid-cols-2">
            <ReportsJarvisLibrary
              reports={allReports}
              selectedId={selectedId}
              onSelect={setSelectedId}
              typeFilter={typeFilter}
              onTypeFilterChange={setTypeFilter}
            />
            <ReportsJarvisViewer
              title={markdown.data?.title ?? "Report"}
              markdown={markdown.data?.markdown}
              isLoading={!!selectedId && markdown.isLoading}
            />
          </div>
        </>
      )}
    </div>
  );
}
