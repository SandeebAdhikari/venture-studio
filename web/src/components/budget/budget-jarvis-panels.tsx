"use client";

import { motion, useReducedMotion } from "framer-motion";
import {
  BudgetAgentUsageList,
  BudgetHistoryChart,
  formatUsd,
} from "@/components/budget/budget-widgets";
import type { BudgetHistoryResponse, BudgetStatusResponse } from "@/types/api";

export function BudgetJarvisAgentsPanel({ status }: { status: BudgetStatusResponse }) {
  const reduceMotion = useReducedMotion();
  const maxCost = Math.max(...status.by_agent.map((a) => a.actual_cost_usd_total), 0.0001);

  return (
    <motion.section
      className="jarvis-panel rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-6 sm:p-8"
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
    >
      <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
        Agent attribution
      </p>
      <h3 className="mt-1 text-lg font-semibold text-foreground">Per-agent spend (today)</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Relative cost share across research agents.
      </p>
      <div className="mt-6">
        <BudgetAgentUsageList agents={status.by_agent} maxCost={maxCost} />
      </div>
    </motion.section>
  );
}

export function BudgetJarvisHistoryPanel({
  history,
}: {
  history: BudgetHistoryResponse | undefined;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.section
      className="jarvis-panel rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-6 sm:p-8"
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
    >
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
            Trend archive
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">14-day burn snapshot</h3>
        </div>
        {history?.generated_at && (
          <p className="font-mono text-[10px] text-muted-foreground">
            Updated {new Date(history.generated_at).toLocaleString()}
          </p>
        )}
      </div>

      {!history ? (
        <div className="h-48 animate-pulse rounded-xl bg-muted/30" />
      ) : history.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No historical usage yet.</p>
      ) : (
        <BudgetHistoryChart items={history.items} />
      )}
    </motion.section>
  );
}
