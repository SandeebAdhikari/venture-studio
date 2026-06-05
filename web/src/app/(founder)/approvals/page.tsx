"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ApprovalsJarvisDetail } from "@/components/approvals/approvals-jarvis-detail";
import { ApprovalsJarvisHero } from "@/components/approvals/approvals-jarvis-hero";
import { ApprovalsJarvisMetrics } from "@/components/approvals/approvals-jarvis-metrics";
import { ApprovalsJarvisQueue } from "@/components/approvals/approvals-jarvis-queue";
import { LiveIndicator, ErrorState } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import type { ApprovalRequestRead, PaginatedResponse } from "@/types/api";

const POLL_INTERVAL = 15_000;

const BOOT_SEQUENCE = [
  "Loading governance queue…",
  "Syncing decision history…",
  "Awaiting founder actions…",
  "Approvals console online.",
];

export default function ApprovalsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();
  const [bootLine, setBootLine] = useState(0);

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

  const stats = useMemo(() => {
    const pending = items.filter((a) => a.status === "pending").length;
    const approved = items.filter((a) => a.status === "approved").length;
    const rejected = items.filter((a) => a.status === "rejected").length;
    return {
      total: approvals.data?.total ?? items.length,
      pending,
      approved,
      rejected,
    };
  }, [items, approvals.data?.total]);

  useEffect(() => {
    if (reduceMotion) return;
    const id = setInterval(() => {
      setBootLine((n) => (n + 1) % BOOT_SEQUENCE.length);
    }, 2200);
    return () => clearInterval(id);
  }, [reduceMotion]);

  if (approvals.error) {
    return (
      <div className="jarvis-page space-y-8">
        <ErrorState message={approvals.error.message} onRetry={() => approvals.mutate()} />
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
            Governance control
          </motion.p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground">Approvals</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Review and action founder approval requests for rankings and venture reports.
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
            onClick={() => approvals.mutate()}
            disabled={approvals.isValidating}
            className="inline-flex h-8 items-center justify-center rounded-lg border border-border bg-card px-3 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            Refresh
          </button>
          <LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />
        </div>
      </div>

      {!approvals.data ? (
        <div className="grid gap-6 lg:grid-cols-5">
          <Skeleton className="h-96 rounded-xl lg:col-span-3" />
          <Skeleton className="h-96 rounded-xl lg:col-span-2" />
        </div>
      ) : (
        <>
          <div className="space-y-4">
            <ApprovalsJarvisHero />
            <ApprovalsJarvisMetrics
              total={stats.total}
              pending={stats.pending}
              approved={stats.approved}
              rejected={stats.rejected}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <ApprovalsJarvisQueue
                items={items}
                selectedId={selected?.id ?? null}
                onSelect={setSelectedId}
                statusFilter={statusFilter}
                subjectFilter={subjectFilter}
                onStatusFilterChange={setStatusFilter}
                onSubjectFilterChange={setSubjectFilter}
              />
            </div>
            <div className="lg:col-span-2">
              <ApprovalsJarvisDetail
                approval={selected}
                onComplete={() => approvals.mutate()}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
