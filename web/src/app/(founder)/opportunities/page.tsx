"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { OpportunityJarvisFilters } from "@/components/opportunities/opportunity-jarvis-filters";
import { OpportunityJarvisHero } from "@/components/opportunities/opportunity-jarvis-hero";
import { OpportunityJarvisMetrics } from "@/components/opportunities/opportunity-jarvis-metrics";
import { OpportunityJarvisInventory } from "@/components/opportunities/opportunity-jarvis-inventory";
import { OpportunityJarvisRanking } from "@/components/opportunities/opportunity-jarvis-ranking";
import { LiveIndicator, ErrorState } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import type {
  DashboardOpportunitiesResponse,
  OpportunityRead,
  PaginatedResponse,
} from "@/types/api";

const POLL_INTERVAL = 20_000;

const BOOT_SEQUENCE = [
  "Indexing venture rankings…",
  "Loading executive scores…",
  "Applying review filters…",
  "Opportunity matrix online.",
];

export default function OpportunitiesPage() {
  const [reviewFilter, setReviewFilter] = useState("");
  const [source, setSource] = useState<"ranking" | "all">("ranking");
  const [searchQuery, setSearchQuery] = useState("");
  const reduceMotion = useReducedMotion();
  const [bootLine, setBootLine] = useState(0);

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

  useEffect(() => {
    if (reduceMotion) return;
    const id = setInterval(() => {
      setBootLine((n) => (n + 1) % BOOT_SEQUENCE.length);
    }, 2300);
    return () => clearInterval(id);
  }, [reduceMotion]);

  const filteredRanking = useMemo(() => {
    const rows = ranking.data?.executive_rankings ?? [];
    let list = rows;
    if (reviewFilter) {
      list = list.filter((r) => r.review_status === reviewFilter);
    }
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      list = list.filter((r) => r.title.toLowerCase().includes(q));
    }
    return list;
  }, [ranking.data?.executive_rankings, reviewFilter, searchQuery]);

  const filteredInventory = useMemo(() => {
    const rows = all.data?.items ?? [];
    const q = searchQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => r.title.toLowerCase().includes(q));
  }, [all.data?.items, searchQuery]);

  const active = source === "ranking" ? ranking : all;
  const visibleCount =
    source === "ranking" ? filteredRanking.length : filteredInventory.length;

  if (active.error) {
    return (
      <div className="jarvis-page space-y-8">
        <ErrorState message={active.error.message} onRetry={() => active.mutate()} />
      </div>
    );
  }

  const isLoading = source === "ranking" ? !ranking.data : !all.data;

  return (
    <div className="jarvis-page space-y-8">
      <div className="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <motion.p
            className="font-mono text-[10px] uppercase tracking-[0.4em] text-[hsl(187_75%_58%)]"
            animate={reduceMotion ? undefined : { opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            Venture intelligence
          </motion.p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground">Opportunities</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Executive rankings and full opportunity inventory from the backend.
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
            onClick={() => {
              ranking.mutate();
              all.mutate();
            }}
            disabled={ranking.isValidating || all.isValidating}
            className="inline-flex h-8 items-center justify-center rounded-lg border border-border bg-card px-3 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            Refresh
          </button>
          <LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />
        </div>
      </div>

      {!isLoading && (
        <div className="space-y-4">
          <OpportunityJarvisHero ranking={ranking.data} />
          <OpportunityJarvisMetrics
            ranking={ranking.data}
            visibleCount={visibleCount}
            inventoryTotal={all.data?.total}
          />
        </div>
      )}

      <OpportunityJarvisFilters
        source={source}
        reviewFilter={reviewFilter}
        searchQuery={searchQuery}
        onSourceChange={setSource}
        onReviewChange={setReviewFilter}
        onSearchChange={setSearchQuery}
      />

      {isLoading ? (
        <div className="space-y-6">
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-96 w-full rounded-xl" />
        </div>
      ) : source === "ranking" ? (
        <OpportunityJarvisRanking
          items={filteredRanking}
          emptyMessage="No ranked opportunities match your filters."
        />
      ) : (
        <OpportunityJarvisInventory
          items={filteredInventory}
          emptyMessage="No opportunities match your filters."
        />
      )}
    </div>
  );
}
