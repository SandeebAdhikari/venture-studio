"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardSummaryResponse } from "@/types/api";

interface DashboardJarvisHeroProps {
  summary: DashboardSummaryResponse;
}

export function DashboardJarvisHero({ summary }: DashboardJarvisHeroProps) {
  const reduceMotion = useReducedMotion();
  const pipelineActive = summary.pipeline.running != null;

  return (
    <motion.section
      className="jarvis-hero-panel relative overflow-hidden rounded-xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <motion.div
        className="jarvis-hud relative flex flex-col justify-center gap-4 p-6 sm:p-8"
        initial={reduceMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 120, damping: 18, delay: 0.05 }}
      >
        <div className="space-y-1">
          <motion.p
            className="jarvis-hud-label font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_80%_65%)]"
            animate={reduceMotion ? undefined : { opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2.4, repeat: Infinity }}
          >
            Venture studio command
          </motion.p>
          <h2 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
            Dashboard overview
          </h2>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Live metrics, pipeline orchestration, agent pulse, and top-ranked opportunities.
          </p>
          <p className="font-mono text-[10px] uppercase tracking-widest text-[hsl(187_65%_50%)]">
            Pipeline · {pipelineActive ? "active" : "idle"}
          </p>
        </div>
      </motion.div>
    </motion.section>
  );
}
