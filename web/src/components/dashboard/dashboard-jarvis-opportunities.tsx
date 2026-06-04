"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import { TableSkeleton } from "@/components/ui/skeleton";
import type { DashboardOpportunitiesResponse } from "@/types/api";

function scoreValue(item: DashboardOpportunitiesResponse["items"][number]): number | null {
  const raw = item.final_opportunity_score ?? item.score;
  return raw != null ? Number(raw) : null;
}

interface DashboardJarvisOpportunitiesProps {
  data: DashboardOpportunitiesResponse | undefined;
  isLoading: boolean;
}

export function DashboardJarvisOpportunities({ data, isLoading }: DashboardJarvisOpportunitiesProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.section
      className="jarvis-panel jarvis-opportunities-panel rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-6 sm:p-8"
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.28 }}
    >
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
            Executive ranking
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">Top opportunities</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Highest-ranked ventures from the dashboard opportunities API.
          </p>
        </div>
        {data && (
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            {data.items.length} of {data.total_opportunities} · v{data.version ?? "—"}
          </p>
        )}
      </div>

      {isLoading && !data ? (
        <TableSkeleton rows={5} cols={4} />
      ) : !data || data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No ranked opportunities yet.</p>
      ) : (
        <ul className="space-y-3">
          {data.items.map((item, i) => {
            const score = scoreValue(item);
            const pct = score != null ? Math.min(100, Math.max(0, score)) : 0;
            return (
              <motion.li
                key={item.opportunity_id}
                className="jarvis-opp-row group rounded-xl border border-[hsl(187_30%_26%/0.45)] bg-gradient-to-r from-[hsl(187_28%_12%/0.35)] to-transparent px-4 py-4 sm:px-5"
                initial={reduceMotion ? false : { opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 * i }}
                whileHover={reduceMotion ? undefined : { borderColor: "hsl(187 55% 45% / 0.55)" }}
              >
                <div className="flex flex-wrap items-start gap-4">
                  <div
                    className={`jarvis-rank-badge flex h-11 w-11 shrink-0 items-center justify-center rounded-lg font-mono text-sm font-bold ${
                      i === 0 ? "jarvis-rank-badge--gold" : ""
                    }`}
                  >
                    {item.rank ?? i + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-foreground">{item.title}</p>
                      {item.is_top_opportunity && (
                        <span className="rounded border border-[hsl(187_60%_45%/0.5)] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-[hsl(187_80%_65%)]">
                          top
                        </span>
                      )}
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-4">
                      <div className="min-w-[140px] flex-1">
                        <div className="mb-1 flex justify-between font-mono text-[10px] text-muted-foreground">
                          <span>Score</span>
                          <span className="text-[hsl(187_85%_72%)]">
                            {score != null ? score.toFixed(1) : "—"}
                          </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-muted/80">
                          <motion.div
                            className="jarvis-score-fill h-full rounded-full"
                            initial={reduceMotion ? false : { width: 0 }}
                            animate={{ width: `${pct}%` }}
                            transition={{ duration: 0.55, delay: 0.08 * i }}
                          />
                        </div>
                      </div>
                      <StatusBadge status={item.review_status} />
                    </div>
                  </div>
                </div>
              </motion.li>
            );
          })}
        </ul>
      )}

      <Link
        href="/opportunities"
        className="jarvis-link mt-6 inline-block font-mono text-xs uppercase tracking-wider text-[hsl(187_75%_60%)]"
      >
        View all opportunities →
      </Link>
    </motion.section>
  );
}
