"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { BudgetJarvisHero } from "@/components/budget/budget-jarvis-hero";
import { BudgetJarvisMetrics } from "@/components/budget/budget-jarvis-metrics";
import {
  BudgetJarvisPanels,
} from "@/components/budget/budget-jarvis-panels";
import { LiveIndicator, ErrorState } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { usePollingApi } from "@/hooks/use-api";
import { buildQuery } from "@/lib/api/client";
import type { BudgetHistoryResponse, BudgetStatusResponse } from "@/types/api";

const POLL_INTERVAL = 30_000;

const BOOT_SEQUENCE = [
  "Syncing LLM spend telemetry…",
  "Loading agent attribution…",
  "Indexing 30-day burn…",
  "Budget console online.",
];

export default function BudgetPage() {
  const reduceMotion = useReducedMotion();
  const [bootLine, setBootLine] = useState(0);

  const status = usePollingApi<BudgetStatusResponse>("budget", POLL_INTERVAL);
  const history = usePollingApi<BudgetHistoryResponse>(
    `budget/history${buildQuery({ days: 30 })}`,
    POLL_INTERVAL,
  );

  useEffect(() => {
    if (reduceMotion) return;
    const id = setInterval(() => {
      setBootLine((n) => (n + 1) % BOOT_SEQUENCE.length);
    }, 2400);
    return () => clearInterval(id);
  }, [reduceMotion]);

  if (status.error) {
    return (
      <div className="jarvis-page space-y-8">
        <ErrorState message={status.error.message} onRetry={() => status.mutate()} />
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
            Spend control
          </motion.p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground">Budget</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Daily LLM spend, per-agent usage, and threshold warnings from the backend.
          </p>
          {!reduceMotion && (
            <p className="mt-2 font-mono text-xs text-[hsl(187_60%_50%)]">
              &gt; {BOOT_SEQUENCE[bootLine]}
            </p>
          )}
          {history.data?.generated_at && (
            <p className="mt-2 text-xs text-muted-foreground">
              History updated {new Date(history.data.generated_at).toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              status.mutate();
              history.mutate();
            }}
            disabled={status.isValidating || history.isValidating}
            className="inline-flex h-8 items-center justify-center rounded-lg border border-border bg-card px-3 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            Refresh
          </button>
          <LiveIndicator intervalSeconds={POLL_INTERVAL / 1000} />
        </div>
      </div>

      {!status.data ? (
        <div className="space-y-6">
          <Skeleton className="h-[280px] w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
      ) : (
        <>
          <div className="space-y-4">
            <BudgetJarvisHero status={status.data} />
            <BudgetJarvisMetrics status={status.data} />
          </div>
          <BudgetJarvisPanels status={status.data} history={history.data} />
        </>
      )}
    </div>
  );
}
