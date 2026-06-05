"use client";

import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import {
  opportunityDimensions,
  opportunityScore,
  scorePercent,
} from "@/lib/opportunities/opportunity-utils";
import type { DashboardOpportunityItem } from "@/types/api";

interface OpportunityJarvisDetailProps {
  item: DashboardOpportunityItem;
}

export function OpportunityJarvisDetail({ item }: OpportunityJarvisDetailProps) {
  const reduceMotion = useReducedMotion();
  const score = opportunityScore(item);
  const pct = scorePercent(score);
  const dimensions = opportunityDimensions(item);

  return (
    <motion.div
      key={item.opportunity_id}
      className="jarvis-stage-lens jarvis-opp-lens relative overflow-hidden rounded-2xl border border-[hsl(187_40%_32%/0.45)] bg-gradient-to-br from-[hsl(187_26%_11%/0.55)] to-transparent p-6"
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 240, damping: 24 }}
    >
      <div className="jarvis-hero-glow pointer-events-none absolute -left-16 top-0 h-48 w-48 opacity-30" aria-hidden />

      <div className="relative flex flex-wrap items-start gap-4">
        <div
          className={`jarvis-rank-badge flex h-14 w-14 shrink-0 items-center justify-center rounded-xl font-mono text-lg font-bold ${
            item.rank === 1 ? "jarvis-rank-badge--gold" : ""
          }`}
        >
          {item.rank ?? "—"}
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
            Inspecting venture
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">{item.title}</h3>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={item.review_status} />
            {item.is_top_opportunity && (
              <span className="rounded border border-[hsl(187_60%_45%/0.5)] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-[hsl(187_80%_65%)]">
                top pick
              </span>
            )}
            <span className="font-mono text-xs text-muted-foreground">
              Confidence {Math.round(item.confidence_score * 100)}%
            </span>
            {item.agent_coverage_count != null && (
              <span className="font-mono text-xs text-muted-foreground">
                · {item.agent_coverage_count} agents
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-[10px] uppercase text-muted-foreground">Final score</p>
          <p className="font-mono text-3xl font-semibold text-[hsl(187_90%_78%)]">
            {score != null ? score.toFixed(1) : "—"}
          </p>
        </div>
      </div>

      <div className="relative mt-5">
        <div className="mb-1 flex justify-between font-mono text-[10px] text-muted-foreground">
          <span>Composite</span>
          <span className="text-[hsl(187_85%_72%)]">{pct.toFixed(0)}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-muted/80">
          <motion.div
            className="jarvis-score-fill h-full rounded-full"
            initial={reduceMotion ? false : { width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6 }}
          />
        </div>
      </div>

      {dimensions.length > 0 && (
        <div className="relative mt-6 grid gap-3 sm:grid-cols-2">
          {dimensions.map((dim, i) => (
            <div key={dim.key} className="rounded-lg border border-[hsl(187_38%_30%/0.25)] bg-black/15 px-3 py-2.5">
              <div className="mb-1 flex justify-between font-mono text-[10px] text-muted-foreground">
                <span>{dim.label}</span>
                <span className="text-[hsl(187_85%_72%)]">{dim.value.toFixed(1)}</span>
              </div>
              <div className="h-1 overflow-hidden rounded-full bg-muted/70">
                <motion.div
                  className="jarvis-score-fill h-full rounded-full"
                  initial={reduceMotion ? false : { width: 0 }}
                  animate={{ width: `${scorePercent(dim.value)}%` }}
                  transition={{ duration: 0.5, delay: 0.05 * i }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
