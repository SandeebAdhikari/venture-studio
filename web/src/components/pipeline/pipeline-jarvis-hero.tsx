"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardPipelineResponse } from "@/types/api";

interface PipelineJarvisHeroProps {
  data: DashboardPipelineResponse;
}

export function PipelineJarvisHero({ data }: PipelineJarvisHeroProps) {
  const reduceMotion = useReducedMotion();
  const isLive = data.running != null;

  return (
    <motion.section
      className="jarvis-hero-panel relative overflow-hidden rounded-xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative space-y-2 p-6 sm:p-8">
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
    </motion.section>
  );
}
