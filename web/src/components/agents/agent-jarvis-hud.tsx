"use client";

import { motion, useReducedMotion } from "framer-motion";
import { AgentStepRail } from "@/components/agents/agent-step-rail";
import type { AgentStepSync } from "@/lib/agents/agent-step-sync";
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

interface AgentJarvisHudProps {
  agents: DashboardAgentStatus[];
  averageCoverage: number | null | undefined;
  stepSync: AgentStepSync;
}

export function AgentJarvisHud({ agents, averageCoverage, stepSync }: AgentJarvisHudProps) {
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
      className="jarvis-hud flex flex-col justify-center gap-5 p-6"
      initial={reduceMotion ? false : { opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 120, damping: 18, delay: 0.15 }}
    >
      <div className="space-y-1">
        <motion.p
          className="jarvis-hud-label font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_80%_65%)]"
          animate={reduceMotion ? undefined : { opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2.4, repeat: Infinity }}
        >
          Intelligence mesh online
        </motion.p>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          Research agent constellation
        </h2>
        <p className="text-sm text-muted-foreground">
          Live orchestration across market, customer, and synthesis agents.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            className="jarvis-hud-metric rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-black/20 px-3 py-2.5"
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              type: "spring",
              stiffness: 280,
              damping: 22,
              delay: 0.2 + i * 0.06,
            }}
            whileHover={reduceMotion ? undefined : { scale: 1.03, borderColor: "hsl(187 80% 55% / 0.6)" }}
          >
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              {m.label}
            </p>
            <p className="mt-1 font-mono text-lg font-medium text-[hsl(187_90%_78%)]">{m.value}</p>
          </motion.div>
        ))}
      </div>

      <AgentStepRail
        sync={stepSync}
        variant="compact"
        showPhaseLabels={false}
        title="Mesh progress"
      />
    </motion.div>
  );
}
