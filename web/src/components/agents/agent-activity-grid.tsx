"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Badge, statusVariant } from "@/components/ui/badge";
import type { DashboardAgentStatus } from "@/types/api";

function successRate(agent: DashboardAgentStatus): number {
  if (agent.current_total <= 0) return 0;
  return Math.round((agent.current_completed / agent.current_total) * 100);
}

function AgentRing({ value, reduceMotion }: { value: number; reduceMotion: boolean }) {
  const r = 36;
  const c = 2 * Math.PI * r;
  const offset = c - (value / 100) * c;

  return (
    <div className="relative h-20 w-20 shrink-0">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 80 80" aria-hidden>
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth="4"
        />
        <motion.circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          stroke="hsl(187 90% 55%)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={c}
          initial={reduceMotion ? { strokeDashoffset: offset } : { strokeDashoffset: c }}
          animate={{ strokeDashoffset: offset }}
          transition={{ type: "spring", stiffness: 60, damping: 14, delay: 0.2 }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-mono text-sm font-semibold text-[hsl(187_85%_75%)]">
        {value}%
      </span>
    </div>
  );
}

const listVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.1 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 28, scale: 0.94 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 320, damping: 26 },
  },
};

export function AgentActivityGrid({ agents }: { agents: DashboardAgentStatus[] | null | undefined }) {
  const reduceMotion = useReducedMotion();
  const list = agents ?? [];

  if (list.length === 0) {
    return (
      <p className="font-mono text-sm text-muted-foreground">
        {"// No agent telemetry in current cycle."}
      </p>
    );
  }

  return (
    <motion.div
      className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
      variants={reduceMotion ? undefined : listVariants}
      initial="hidden"
      animate="show"
    >
      {list.map((agent) => {
        const rate = successRate(agent);
        const status =
          agent.current_failed > 0 ? "degraded" : rate >= 80 ? "optimal" : "active";

        return (
          <motion.article
            key={agent.agent}
            variants={reduceMotion ? undefined : cardVariants}
            whileHover={
              reduceMotion
                ? undefined
                : {
                    y: -6,
                    scale: 1.02,
                    boxShadow: "0 0 32px hsl(187 80% 50% / 0.15)",
                  }
            }
            transition={{ type: "spring", stiffness: 400, damping: 28 }}
            className="jarvis-agent-card group relative overflow-hidden rounded-xl border border-[hsl(187_40%_35%/0.4)] bg-card/80 p-5 backdrop-blur-sm"
          >
            <motion.div
              className="jarvis-card-scan pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[hsl(187_90%_60%)] to-transparent"
              animate={reduceMotion ? undefined : { top: ["0%", "100%", "0%"] }}
              transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
            />

            <div className="flex items-start gap-4">
              <AgentRing value={rate} reduceMotion={!!reduceMotion} />
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-widest text-[hsl(187_70%_55%)]">
                      {status}
                    </p>
                    <h3 className="mt-0.5 truncate text-base font-semibold text-foreground">
                      {agent.display_name}
                    </h3>
                  </div>
                  <Badge variant={agent.current_failed > 0 ? "warning" : "success"}>
                    {agent.current_total} runs
                  </Badge>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-md border border-border/60 bg-muted/30 py-2">
                    <p className="font-mono font-semibold text-[hsl(187_85%_70%)]">
                      {agent.current_completed}
                    </p>
                    <p className="text-muted-foreground">Done</p>
                  </div>
                  <div className="rounded-md border border-border/60 bg-muted/30 py-2">
                    <p className="font-mono font-semibold text-muted-foreground">
                      {agent.current_skipped}
                    </p>
                    <p className="text-muted-foreground">Skip</p>
                  </div>
                  <div className="rounded-md border border-border/60 bg-muted/30 py-2">
                    <p className="font-mono font-semibold text-foreground/60">
                      {agent.current_failed}
                    </p>
                    <p className="text-muted-foreground">Fail</p>
                  </div>
                </div>
              </div>
            </div>

            <motion.div
              className="mt-4 h-1 overflow-hidden rounded-full bg-muted"
              layout
            >
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-[hsl(187_60%_35%)] to-[hsl(187_90%_65%)]"
                initial={{ width: 0 }}
                animate={{ width: `${rate}%` }}
                transition={{ type: "spring", stiffness: 80, damping: 18, delay: 0.15 }}
              />
            </motion.div>
          </motion.article>
        );
      })}
    </motion.div>
  );
}

export function AgentCompactList({ agents }: { agents: DashboardAgentStatus[] | null | undefined }) {
  const list = agents ?? [];
  return (
    <div className="space-y-2">
      {list.map((agent) => (
        <div
          key={agent.agent}
          className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-4 py-3 text-sm"
        >
          <span className="font-medium">{agent.display_name}</span>
          <div className="flex gap-2">
            <Badge variant={statusVariant("completed")}>{agent.current_completed}</Badge>
            {agent.current_failed > 0 && (
              <Badge variant={statusVariant("failed")}>{agent.current_failed}</Badge>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
