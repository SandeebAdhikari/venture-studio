"use client";

import { motion, useReducedMotion } from "framer-motion";
import { BudgetWarningsList, formatUsd } from "@/components/budget/budget-widgets";
import type { BudgetStatusResponse } from "@/types/api";

export function BudgetJarvisMetrics({ status }: { status: BudgetStatusResponse }) {
  const reduceMotion = useReducedMotion();

  const metrics = [
    { label: "Daily budget", value: formatUsd(status.budget_usd), hint: status.usage_date },
    {
      label: "Spent today",
      value: formatUsd(status.spent_usd, 4),
      hint: `${status.calls_total} LLM calls`,
    },
    { label: "Remaining", value: formatUsd(status.remaining_usd, 4), hint: "available today" },
    {
      label: "Estimated",
      value: formatUsd(status.estimated_cost_usd_total, 4),
      hint: "model projection",
    },
  ];

  const tokens = [
    { label: "Prompt", value: status.prompt_tokens_total.toLocaleString() },
    { label: "Completion", value: status.completion_tokens_total.toLocaleString() },
  ];

  return (
    <div className="space-y-4">
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
            transition={{ delay: 0.1 + i * 0.05 }}
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

      <motion.div
        className="flex flex-wrap items-center gap-4 rounded-lg border border-[hsl(187_35%_28%/0.35)] bg-[hsl(var(--card)/0.4)] px-4 py-3"
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12 }}
      >
        <div className="flex gap-4">
          {tokens.map((t) => (
            <div key={t.label}>
              <p className="font-mono text-[9px] uppercase text-muted-foreground">{t.label}</p>
              <p className="font-mono text-sm text-[hsl(187_85%_72%)]">{t.value}</p>
            </div>
          ))}
        </div>
        <div className="min-w-0 flex-1">
          <p className="mb-2 font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
            Thresholds
          </p>
          <BudgetWarningsList warnings={status.warnings} />
        </div>
      </motion.div>
    </div>
  );
}
