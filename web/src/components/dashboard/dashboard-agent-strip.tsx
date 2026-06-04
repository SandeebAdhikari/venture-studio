"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardAgentStatus } from "@/types/api";

function successRate(agent: DashboardAgentStatus): number {
  if (agent.current_total <= 0) return 0;
  return Math.round((agent.current_completed / agent.current_total) * 100);
}

export function DashboardAgentStrip({
  agents,
}: {
  agents: DashboardAgentStatus[] | null | undefined;
}) {
  const reduceMotion = useReducedMotion();
  const list = agents ?? [];

  return (
    <div className="space-y-2">
      {list.map((agent, i) => {
        const rate = successRate(agent);
        return (
          <motion.div
            key={agent.agent}
            className="jarvis-strip-row group relative overflow-hidden rounded-lg border border-[hsl(187_35%_28%/0.4)] bg-[hsl(187_25%_10%/0.25)] px-4 py-3"
            initial={reduceMotion ? false : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{agent.display_name}</p>
                <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {agent.current_completed} completed · {agent.current_failed} failed
                </p>
              </div>
              <span className="shrink-0 font-mono text-sm text-[hsl(187_85%_72%)]">{rate}%</span>
            </div>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted/80">
              <motion.div
                className="h-full rounded-full bg-[hsl(187_85%_55%)]"
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
