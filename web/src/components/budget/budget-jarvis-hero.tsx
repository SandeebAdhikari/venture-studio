"use client";

import { motion, useReducedMotion } from "framer-motion";
import { formatPercent, formatUsd } from "@/lib/utils";
import type { BudgetStatusResponse } from "@/types/api";

export function BudgetJarvisHero({ status }: { status: BudgetStatusResponse }) {
  const reduceMotion = useReducedMotion();
  const displayPct = Math.min(Math.max(status.utilization_pct, 0), 100);

  return (
    <motion.section
      className="jarvis-hero-panel budget-jarvis-hero relative overflow-hidden rounded-2xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative p-6 sm:p-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1.5">
            <motion.p
              className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_80%_65%)]"
              animate={reduceMotion ? undefined : { opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2.2, repeat: Infinity }}
            >
              LLM spend telemetry
            </motion.p>

            <h2 className="text-2xl font-semibold tracking-tight text-foreground">Budget command</h2>

            <p className="max-w-2xl text-sm text-muted-foreground">
              Daily utilization against your LLM spend cap.
              {status.budget_exceeded && (
                <span className="ml-1 font-medium text-destructive">Daily cap exceeded.</span>
              )}
            </p>
          </div>

          <div className="flex flex-col items-start gap-2 sm:items-end sm:text-right">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 sm:justify-end">
              <p
                className={`font-mono text-3xl font-bold tabular-nums sm:text-4xl ${
                  status.budget_exceeded ? "text-destructive" : "text-[hsl(187_92%_78%)]"
                }`}
              >
                {formatPercent(displayPct)}
              </p>
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {status.budget_exceeded ? "limit exceeded" : "utilization"}
              </span>
            </div>

            <div
              className="h-2 w-full min-w-[12rem] overflow-hidden rounded-full bg-[hsl(187_30%_18%/0.6)] sm:w-48"
              role="progressbar"
              aria-valuenow={displayPct}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className={`h-full rounded-full transition-all ${
                  status.budget_exceeded ? "bg-destructive" : "bg-[hsl(187_75%_55%)]"
                }`}
                style={{ width: `${displayPct}%` }}
              />
            </div>

            <div className="flex gap-4 font-mono text-[10px] text-muted-foreground">
              <span>Spent {formatUsd(status.spent_usd, 4)}</span>
              <span>Cap {formatUsd(status.budget_usd)}</span>
            </div>
          </div>
        </div>
      </div>
    </motion.section>
  );
}
