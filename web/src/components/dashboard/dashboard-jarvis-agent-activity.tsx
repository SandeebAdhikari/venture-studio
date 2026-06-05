"use client";

import Link from "next/link";
import { ChevronDown } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { DashboardAgentStrip } from "@/components/dashboard/dashboard-agent-strip";
import { cn } from "@/lib/utils";
import type { DashboardAgentStatus } from "@/types/api";

const COLLAPSED_AGENT_COUNT = 2;

interface DashboardJarvisAgentActivityProps {
  agents: DashboardAgentStatus[];
  activeAgentKey?: string | null;
  canViewAgents: boolean;
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
}

export function DashboardJarvisAgentActivity({
  agents,
  activeAgentKey,
  canViewAgents,
  expanded,
  onExpandedChange,
}: DashboardJarvisAgentActivityProps) {
  const reduceMotion = useReducedMotion();
  const hasMoreAgents = agents.length > COLLAPSED_AGENT_COUNT;
  const visibleAgents = expanded || !hasMoreAgents ? agents : agents.slice(0, COLLAPSED_AGENT_COUNT);

  const expandButton = (
    <button
      type="button"
      onClick={() => onExpandedChange(!expanded)}
      className="mt-4 flex w-full shrink-0 items-center justify-center gap-1.5 rounded-lg border border-[hsl(187_35%_28%/0.4)] bg-[hsl(187_24%_10%/0.25)] py-2 font-mono text-[10px] uppercase tracking-wider text-[hsl(187_75%_60%)] transition-colors hover:border-[hsl(187_55%_45%/0.55)] hover:text-[hsl(187_85%_72%)]"
    >
      {expanded ? (
        <>
          Show less
          <ChevronDown className="h-3.5 w-3.5 rotate-180" aria-hidden />
        </>
      ) : (
        <>
          {hasMoreAgents ? `Show all ${agents.length} agents` : "Show full agent activity"}
          <ChevronDown className="h-3.5 w-3.5" aria-hidden />
        </>
      )}
    </button>
  );

  return (
    <motion.div
      className={cn(
        "jarvis-panel flex w-full flex-col rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.65)] p-6",
        expanded ? "h-fit self-start" : "h-full min-h-0",
      )}
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.22 }}
    >
      <div className="shrink-0">
        <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
          Research mesh
        </p>
        <h3 className="mt-1 text-lg font-semibold text-foreground">Agent activity</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Completion pulse across active research agents.
        </p>
      </div>

      <div className="mt-4 flex min-h-0 flex-1 flex-col">
        <div className="shrink-0">
          <DashboardAgentStrip agents={visibleAgents} activeAgentKey={activeAgentKey} />
        </div>

        {expandButton}

        {!expanded && <div className="min-h-0 flex-1" aria-hidden />}
      </div>

      {canViewAgents && (
        <Link
          href="/agents"
          className="jarvis-link mt-auto shrink-0 pt-5 font-mono text-xs uppercase tracking-wider text-[hsl(187_75%_60%)]"
        >
          Open agent activity →
        </Link>
      )}
    </motion.div>
  );
}
