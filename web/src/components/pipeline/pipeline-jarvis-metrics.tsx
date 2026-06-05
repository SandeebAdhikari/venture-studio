"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardPipelineResponse } from "@/types/api";

interface PipelineJarvisMetricsProps {
  data: DashboardPipelineResponse;
}

export function PipelineJarvisMetrics({ data }: PipelineJarvisMetricsProps) {
  const reduceMotion = useReducedMotion();
  const latest = data.latest_detail?.run;
  const stageCount = data.stage_order.length || data.latest_detail?.stage_runs.length || 0;
  const isLive = data.running != null;

  const metrics = [
    { label: "Total runs", value: String(data.runs.total) },
    { label: "Orchestrator", value: isLive ? "EXEC" : "IDLE" },
    {
      label: "Latest stages",
      value: latest ? `${latest.stages_completed}/${stageCount || "?"}` : "—",
    },
    {
      label: "Latest status",
      value: latest?.status ?? "—",
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
