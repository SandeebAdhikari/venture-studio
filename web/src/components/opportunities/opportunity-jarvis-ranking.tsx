"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import { OpportunityJarvisDetail } from "@/components/opportunities/opportunity-jarvis-detail";
import {
  opportunityScore,
  scorePercent,
} from "@/lib/opportunities/opportunity-utils";
import type { DashboardOpportunityItem } from "@/types/api";

interface OpportunityJarvisRankingProps {
  items: DashboardOpportunityItem[];
  emptyMessage: string;
}

function defaultSelected(items: DashboardOpportunityItem[]): string | null {
  if (items.length === 0) return null;
  const top = items.find((i) => i.rank === 1) ?? items[0];
  return top.opportunity_id;
}

export function OpportunityJarvisRanking({ items, emptyMessage }: OpportunityJarvisRankingProps) {
  const reduceMotion = useReducedMotion();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const sorted = useMemo(
    () => [...items].sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999)),
    [items],
  );

  const activeId = selectedId ?? defaultSelected(sorted);
  const active = sorted.find((i) => i.opportunity_id === activeId) ?? null;
  const podium = sorted.slice(0, 3);
  const rest = sorted.slice(3);
  const topStrip = sorted.slice(0, Math.min(12, sorted.length));

  useEffect(() => {
    const pick = defaultSelected(sorted);
    if (!pick) return;
    setSelectedId((prev) => {
      if (prev && sorted.some((i) => i.opportunity_id === prev)) return prev;
      return pick;
    });
  }, [sorted]);

  if (sorted.length === 0) {
    return (
      <p className="jarvis-panel rounded-2xl border border-[hsl(187_35%_28%/0.4)] p-8 text-center text-sm text-muted-foreground">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {podium.length > 0 && (
        <div
          className={`jarvis-opp-podium grid items-end gap-3 sm:gap-4 ${
            podium.length >= 3 ? "grid-cols-3" : podium.length === 2 ? "grid-cols-2" : "grid-cols-1"
          }`}
        >
          {(podium.length >= 3
            ? [podium[1], podium[0], podium[2]]
            : podium.length === 2
              ? [podium[1], podium[0]]
              : [podium[0]]
          )
            .filter(Boolean)
            .map((item, idx) => {
            const place = item.rank ?? idx + 1;
            const isFirst = place === 1;
            return (
              <motion.button
                key={item.opportunity_id}
                type="button"
                onClick={() => setSelectedId(item.opportunity_id)}
                className={`jarvis-opp-podium-slot flex flex-col items-center rounded-xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(187_24%_10%/0.45)] px-3 py-4 text-center transition-colors ${
                  isFirst ? "jarvis-opp-podium-slot--first" : podium.length >= 3 ? "pb-6" : ""
                } ${activeId === item.opportunity_id ? "jarvis-opp-podium-slot--active" : ""}`}
              >
                <span
                  className={`jarvis-rank-badge mb-2 flex items-center justify-center rounded-full font-mono font-bold ${
                    isFirst ? "jarvis-rank-badge--gold h-14 w-14 text-lg" : "h-11 w-11 text-sm"
                  }`}
                >
                  {place}
                </span>
                <p className="line-clamp-2 text-sm font-medium text-foreground">{item.title}</p>
                <p className="mt-1 font-mono text-xs text-[hsl(187_85%_72%)]">
                  {opportunityScore(item)?.toFixed(1) ?? "—"}
                </p>
              </motion.button>
            );
          })}
        </div>
      )}

      {topStrip.length > 0 && (
        <div
          className="jarvis-opp-rank-strip relative rounded-xl border border-[hsl(187_35%_28%/0.35)] bg-[hsl(187_22%_8%/0.35)] px-3 py-4"
          style={{ "--rank-count": topStrip.length } as CSSProperties}
        >
          <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
            Rank selector
          </p>
          <div className="jarvis-opp-rank-grid relative">
            <div className="jarvis-filmstrip-track pointer-events-none absolute inset-x-0 top-[1.125rem] z-0 hidden h-px sm:block" />
            {topStrip.map((item, index) => {
              const isActive = item.opportunity_id === activeId;
              const rank = item.rank ?? index + 1;
              return (
                <button
                  key={item.opportunity_id}
                  type="button"
                  onClick={() => setSelectedId(item.opportunity_id)}
                  className="jarvis-filmstrip-node relative z-10"
                  aria-pressed={isActive}
                >
                  <span
                    className={`jarvis-stage-node jarvis-stage-node--completed relative mx-auto flex h-9 w-9 items-center justify-center rounded-full border font-mono text-[10px] font-semibold ${
                      isActive ? "jarvis-stage-node--focus" : ""
                    } ${rank === 1 ? "jarvis-rank-node--gold" : ""}`}
                  >
                    {String(rank).padStart(2, "0")}
                  </span>
                  <span className="jarvis-filmstrip-label mt-2 text-[8px] sm:text-[9px]">
                    #{rank}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {active && <OpportunityJarvisDetail item={active} />}

      {rest.length > 0 && (
        <ul className="jarvis-panel space-y-2 rounded-2xl border border-[hsl(187_35%_28%/0.4)] p-4 sm:p-5">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.35em] text-muted-foreground">
            Full ranking
          </p>
          {rest.map((item, i) => {
            const score = opportunityScore(item);
            const pct = scorePercent(score);
            const isActive = item.opportunity_id === activeId;
            return (
              <li key={item.opportunity_id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(item.opportunity_id)}
                  className={`jarvis-stage-index-row flex w-full flex-col gap-2 rounded-lg px-3 py-3 text-left sm:flex-row sm:items-center ${
                    isActive ? "jarvis-stage-index-row--active" : ""
                  }`}
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <span className="jarvis-rank-badge flex h-9 w-9 shrink-0 items-center justify-center rounded-lg font-mono text-xs font-bold">
                      {item.rank ?? i + 4}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">{item.title}</span>
                    <StatusBadge status={item.review_status} />
                  </div>
                  <div className="flex items-center gap-3 sm:w-48">
                    <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted/80">
                      <div className="jarvis-score-fill h-full rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="shrink-0 font-mono text-xs text-[hsl(187_85%_72%)]">
                      {score?.toFixed(1) ?? "—"}
                    </span>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {rest.length === 0 && sorted.length <= 3 && active && (
        <p className="text-center text-xs text-muted-foreground">
          Select a podium venture above to inspect scores.
        </p>
      )}
    </div>
  );
}
