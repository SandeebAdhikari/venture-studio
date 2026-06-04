"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardPipelineResponse } from "@/types/api";

interface PipelineJarvisHeroProps {
  data: DashboardPipelineResponse;
}

export function PipelineJarvisHero({ data }: PipelineJarvisHeroProps) {
  const reduceMotion = useReducedMotion();
  const latest = data.latest_detail?.run;
  const stageCount = data.latest_detail?.stage_runs.length ?? data.stage_order.length;
  const isLive = data.running != null;

  const metrics = [
    { label: "Total runs", value: String(data.runs.total) },
    { label: "Orchestrator", value: isLive ? "EXEC" : "IDLE" },
    {
      label: "Latest stages",
      value: latest
        ? `${latest.stages_completed}/${stageCount || "?"}`
        : "—",
    },
    {
      label: "Latest status",
      value: latest?.status ?? "—",
    },
  ];

  return (
    <motion.section
      className="jarvis-hero-panel relative overflow-hidden rounded-xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative grid gap-6 p-6 sm:p-8 lg:grid-cols-[1fr_auto] lg:items-center">
        <div className="space-y-2">
          <motion.p
            className="jarvis-hud-label font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_80%_65%)]"
            animate={reduceMotion ? undefined : { opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2.2, repeat: Infinity }}
          >
            Backend orchestrator
          </motion.p>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            Pipeline command telemetry
          </h2>
          <p className="max-w-xl text-sm text-muted-foreground">
            Monitor stage-level execution, active runs, and historical orchestration from the
            dashboard pipeline API.
          </p>
          <span
            className={`jarvis-status-pill inline-block rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider ${
              isLive ? "jarvis-status-pill--active" : "jarvis-status-pill--idle"
            }`}
          >
            {isLive ? "run in flight" : "awaiting trigger"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:max-w-md">
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              className="jarvis-hud-metric rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-black/20 px-3 py-2.5"
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 + i * 0.05 }}
            >
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {m.label}
              </p>
              <p className="mt-1 font-mono text-base font-medium text-[hsl(187_90%_78%)]">
                {m.value}
              </p>
            </motion.div>
          ))}
        </div>
      </div>

      <motion.div className="relative mx-6 mb-6 h-1 overflow-hidden rounded-full bg-muted sm:mx-8">
        <motion.div
          className="h-full w-1/4 rounded-full bg-[hsl(187_90%_60%)]"
          animate={reduceMotion ? undefined : { x: ["-120%", "420%"] }}
          transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
        />
      </motion.div>
    </motion.section>
  );
}
