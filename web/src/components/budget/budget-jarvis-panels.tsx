"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  BudgetAgentUsageList,
  BudgetHistoryChart,
} from "@/components/budget/budget-widgets";
import type { BudgetHistoryResponse, BudgetStatusResponse } from "@/types/api";

const COLLAPSED_AGENT_COUNT = 2;

interface BudgetJarvisAgentsPanelProps {
  status: BudgetStatusResponse;
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
}

export function BudgetJarvisAgentsPanel({
  status,
  expanded,
  onExpandedChange,
}: BudgetJarvisAgentsPanelProps) {
  const reduceMotion = useReducedMotion();
  const maxCost = Math.max(...status.by_agent.map((a) => a.actual_cost_usd_total), 0.0001);
  const sorted = [...status.by_agent].sort(
    (a, b) => b.actual_cost_usd_total - a.actual_cost_usd_total,
  );
  const canExpand = sorted.length > COLLAPSED_AGENT_COUNT;
  const visibleAgents = expanded ? sorted : sorted.slice(0, COLLAPSED_AGENT_COUNT);

  return (
    <motion.section
      className={cn(
        "jarvis-panel flex w-full flex-col rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-6 sm:p-8",
        expanded ? "h-fit self-start" : "h-full min-h-0",
      )}
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
    >
      <div className="shrink-0">
        <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
          Agent attribution
        </p>
        <h3 className="mt-1 text-lg font-semibold text-foreground">Per-agent spend (today)</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Relative cost share across research agents.
        </p>
      </div>

      <div className="mt-6 flex min-h-0 flex-1 flex-col">
        <div className={expanded ? undefined : "min-h-0 flex-1"}>
          <BudgetAgentUsageList agents={visibleAgents} maxCost={maxCost} />
        </div>
        {canExpand && (
          <button
            type="button"
            onClick={() => onExpandedChange(!expanded)}
            className="mt-4 flex w-full shrink-0 items-center justify-center gap-1.5 rounded-lg border border-[hsl(187_35%_28%/0.4)] bg-[hsl(187_24%_10%/0.25)] py-2 font-mono text-[10px] uppercase tracking-wider text-[hsl(187_75%_60%)] transition-colors hover:border-[hsl(187_55%_45%/0.55)] hover:text-[hsl(187_85%_72%)]"
          >
            {expanded ? "Show fewer agents" : `Show all ${sorted.length} agents`}
            <ChevronDown
              className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")}
              aria-hidden
            />
          </button>
        )}
      </div>
    </motion.section>
  );
}

interface BudgetJarvisHistoryPanelProps {
  history: BudgetHistoryResponse | undefined;
  matchHeight?: boolean;
}

export function BudgetJarvisHistoryPanel({
  history,
  matchHeight = true,
}: BudgetJarvisHistoryPanelProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.section
      className={cn(
        "jarvis-panel w-full rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-6 sm:p-8",
        matchHeight ? "h-full min-h-0" : "h-fit self-start",
      )}
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
      ) : (
        <BudgetHistoryChart items={history.items} />
      )}
    </motion.section>
  );
}

export function BudgetJarvisPanels({
  status,
  history,
}: {
  status: BudgetStatusResponse;
  history: BudgetHistoryResponse | undefined;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={cn(
        "grid gap-6 lg:grid-cols-2",
        expanded ? "items-start" : "items-stretch",
      )}
    >
      <BudgetJarvisAgentsPanel
        status={status}
        expanded={expanded}
        onExpandedChange={setExpanded}
      />
      <BudgetJarvisHistoryPanel history={history} matchHeight={!expanded} />
    </div>
  );
}
