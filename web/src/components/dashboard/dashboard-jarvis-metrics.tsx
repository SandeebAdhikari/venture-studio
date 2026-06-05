"use client";

import { motion, useReducedMotion } from "framer-motion";
import { formatUsd } from "@/lib/utils";
import type { DashboardSummaryResponse } from "@/types/api";

interface DashboardJarvisMetricsProps {
  summary: DashboardSummaryResponse;
}

export function DashboardJarvisMetrics({ summary }: DashboardJarvisMetricsProps) {
  const reduceMotion = useReducedMotion();

  const metrics = [
    {
      label: "Opportunities",
      value: String(summary.opportunities.total),
      hint: `${summary.research.opportunities_total} in research`,
    },
    {
      label: "Signals classified",
      value: String(summary.classification.signals_classified),
      hint: `${summary.collection.signals_pending} pending`,
    },
    {
      label: "LLM spend today",
      value: formatUsd(summary.classification.llm_cost_usd_total, 4),
      hint: `${summary.classification.llm_calls_total} calls`,
    },
    {
      label: "Ranked",
      value: String(summary.ranking.ranked_opportunity_count),
      hint:
        summary.ranking.version != null
          ? `Ranking v${summary.ranking.version}`
          : "Awaiting ranking",
    },
  ];

  return (
    <motion.div
      className="grid grid-cols-2 gap-3 sm:grid-cols-4"
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 120, damping: 20, delay: 0.08 }}
    >
      {metrics.map((m, i) => (
        <motion.div
          key={m.label}
          className="jarvis-hud-metric rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-[hsl(var(--card)/0.55)] px-3 py-2.5"
          initial={reduceMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            type: "spring",
            stiffness: 280,
            damping: 22,
            delay: 0.1 + i * 0.05,
          }}
          whileHover={
            reduceMotion ? undefined : { scale: 1.03, borderColor: "hsl(187 80% 55% / 0.6)" }
          }
        >
          <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            {m.label}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <p className="font-mono text-lg font-medium tabular-nums text-[hsl(187_90%_78%)]">
              {m.value}
            </p>
            <span className="inline-flex rounded-full border border-[hsl(187_45%_38%/0.45)] bg-[hsl(187_28%_12%/0.6)] px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide text-[hsl(187_75%_62%)]">
              {m.hint}
            </span>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}
