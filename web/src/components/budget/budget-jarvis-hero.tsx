"use client";

import { motion, useReducedMotion } from "framer-motion";
import { BudgetJarvisGauge } from "@/components/budget/budget-jarvis-gauge";
import { BudgetWarningsList, formatUsd } from "@/components/budget/budget-widgets";
import type { BudgetStatusResponse } from "@/types/api";

export function BudgetJarvisHero({ status }: { status: BudgetStatusResponse }) {
  const reduceMotion = useReducedMotion();

  const metrics = [
    { label: "Daily budget", value: formatUsd(status.budget_usd), hint: status.usage_date },
    { label: "Spent today", value: formatUsd(status.spent_usd, 4), hint: `${status.calls_total} LLM calls` },
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
    <motion.section
      className="jarvis-hero-panel budget-jarvis-hero relative overflow-hidden rounded-2xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />
      <div className="budget-hero-scan pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative grid gap-8 p-6 sm:p-8 lg:grid-cols-[auto_1fr] lg:gap-10">
        <BudgetJarvisGauge
          utilizationPct={status.utilization_pct}
          budgetExceeded={status.budget_exceeded}
          spentUsd={status.spent_usd}
          budgetUsd={status.budget_usd}
          remainingUsd={status.remaining_usd}
          warnings={status.warnings}
        />

        <div className="flex flex-col justify-center gap-6">
          <div>
            <motion.p
              className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_80%_65%)]"
              animate={reduceMotion ? undefined : { opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2.2, repeat: Infinity }}
            >
              LLM spend telemetry
            </motion.p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">
              Budget command
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Live burn rate and threshold status from the budget API.
              {status.budget_exceeded && (
                <span className="ml-1 font-medium text-destructive">Daily cap exceeded.</span>
              )}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {metrics.map((m, i) => (
              <motion.div
                key={m.label}
                className="jarvis-hud-metric rounded-xl border border-[hsl(187_50%_40%/0.35)] bg-black/25 px-4 py-3"
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.06 * i }}
              >
                <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {m.label}
                </p>
                <p className="mt-1 font-mono text-xl font-medium text-[hsl(187_90%_78%)]">{m.value}</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">{m.hint}</p>
              </motion.div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-4 border-t border-[hsl(187_35%_28%/0.35)] pt-4">
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
          </div>
        </div>
      </div>
    </motion.section>
  );
}
