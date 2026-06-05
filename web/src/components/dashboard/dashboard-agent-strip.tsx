"use client";

import { motion, useReducedMotion } from "framer-motion";
import { sortAgentsByPipeline } from "@/lib/agents/pipeline-order";
import type { DashboardAgentStatus } from "@/types/api";

function successRate(agent: DashboardAgentStatus): number {
  if (agent.current_total <= 0) return 0;
  return Math.round((agent.current_completed / agent.current_total) * 100);
}

export function DashboardAgentStrip({
  agents,
  activeAgentKey,
}: {
  agents: DashboardAgentStatus[] | null | undefined;
  activeAgentKey?: string | null;
}) {
  const reduceMotion = useReducedMotion();
  const list = sortAgentsByPipeline(agents ?? []);

  if (list.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No agent telemetry yet. Run the research pipeline to populate completion stats.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {list.map((agent, i) => {
        const rate = successRate(agent);
        const isActive = activeAgentKey != null && agent.agent === activeAgentKey;
        return (
          <motion.div
            key={agent.agent}
            className={`jarvis-strip-row group relative overflow-hidden rounded-lg border px-4 py-3 ${
              isActive
                ? "border-[hsl(187_55%_50%/0.7)] bg-[hsl(187_30%_14%/0.45)] shadow-[0_0_20px_hsl(187_90%_55%/0.12)]"
                : "border-[hsl(187_35%_28%/0.4)] bg-[hsl(187_25%_10%/0.25)]"
            }`}
            initial={reduceMotion ? false : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{agent.display_name}</p>
                <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {isActive && (
                    <span className="mr-2 text-[hsl(187_85%_72%)]">Executing · </span>
                  )}
                  {agent.current_completed} completed · {agent.current_failed} failed
                </p>
              </div>
              <span className="shrink-0 font-mono text-sm text-[hsl(187_85%_72%)]">{rate}%</span>
            </div>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted/80">
              <motion.div
                className={`h-full rounded-full ${isActive ? "bg-[hsl(187_92%_65%)]" : "bg-[hsl(187_85%_55%)]"}`}
                initial={reduceMotion ? false : { width: 0 }}
                animate={{ width: `${rate}%` }}
                transition={{ duration: 0.6, delay: 0.1 + i * 0.04 }}
              />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
