"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardAgentStatus } from "@/types/api";

function totals(agents: DashboardAgentStatus[]) {
  return agents.reduce(
    (acc, a) => ({
      completed: acc.completed + a.current_completed,
      failed: acc.failed + a.current_failed,
      skipped: acc.skipped + a.current_skipped,
      total: acc.total + a.current_total,
    }),
    { completed: 0, failed: 0, skipped: 0, total: 0 },
  );
}

interface AgentJarvisMetricsProps {
  agents: DashboardAgentStatus[];
  averageCoverage: number | null | undefined;
}

export function AgentJarvisMetrics({ agents, averageCoverage }: AgentJarvisMetricsProps) {
  const reduceMotion = useReducedMotion();
  const stats = totals(agents);
  const successPct =
    stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  const metrics = [
    { label: "Active agents", value: String(agents.length) },
    { label: "Total runs", value: String(stats.total) },
    { label: "Success rate", value: `${successPct}%` },
    {
      label: "Coverage index",
      value: averageCoverage != null ? averageCoverage.toFixed(2) : "—",
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
          <p className="mt-1.5 font-mono text-lg font-medium tabular-nums text-[hsl(187_90%_78%)]">
            {m.value}
          </p>
        </motion.div>
      ))}
    </motion.div>
  );
}
