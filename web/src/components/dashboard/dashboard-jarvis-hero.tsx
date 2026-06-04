"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { formatUsd } from "@/lib/utils";
import type { DashboardSummaryResponse } from "@/types/api";

const DashboardJarvisCore = dynamic(
  () => import("@/components/dashboard/dashboard-jarvis-core").then((m) => m.DashboardJarvisCore),
  { ssr: false },
);

interface DashboardJarvisHeroProps {
  summary: DashboardSummaryResponse;
}

export function DashboardJarvisHero({ summary }: DashboardJarvisHeroProps) {
  const reduceMotion = useReducedMotion();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const sync = () => setIsMobile(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  const pipelineActive = summary.pipeline.running != null;
  const metrics = [
    {
      label: "Opportunities",
      value: String(summary.opportunities.total),
      hint: `${summary.research.opportunities_total} in research`,
    },
    {
      label: "Signals classified",
      value: String(summary.classification.signals_classified),
      hint: `${summary.collection.signals_pending} pending`,
    },
    {
      label: "LLM spend today",
      value: formatUsd(summary.classification.llm_cost_usd_total, 4),
      hint: `${summary.classification.llm_calls_total} calls`,
    },
    {
      label: "Ranked",
      value: String(summary.ranking.ranked_opportunity_count),
      hint:
        summary.ranking.version != null
          ? `Ranking v${summary.ranking.version}`
          : "Awaiting ranking",
    },
  ];

  return (
    <motion.section
      className="jarvis-hero-panel relative overflow-hidden rounded-xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative grid min-h-[300px] lg:grid-cols-[1.05fr_1fr]">
        <div className="relative flex items-center justify-center p-4 lg:p-6">
          <DashboardJarvisCore
            summary={summary}
            reducedMotion={!!reduceMotion}
            isMobile={isMobile}
          />
        </div>

        <motion.div
          className="jarvis-hud flex flex-col justify-center gap-5 p-6"
          initial={reduceMotion ? false : { opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ type: "spring", stiffness: 120, damping: 18, delay: 0.1 }}
        >
          <div className="space-y-1">
            <motion.p
              className="jarvis-hud-label font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_80%_65%)]"
              animate={reduceMotion ? undefined : { opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2.4, repeat: Infinity }}
            >
              Venture studio command
            </motion.p>
            <h2 className="text-xl font-semibold tracking-tight text-foreground">
              Studio intelligence overview
            </h2>
            <p className="text-sm text-muted-foreground">
              Live metrics from dashboard summary — pipeline, research, and ranking.
            </p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-[hsl(187_65%_50%)]">
              Pipeline · {pipelineActive ? "executing" : "idle"}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {metrics.map((m, i) => (
              <motion.div
                key={m.label}
                className="jarvis-hud-metric rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-black/20 px-3 py-2.5"
                initial={reduceMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  type: "spring",
                  stiffness: 280,
                  damping: 22,
                  delay: 0.15 + i * 0.05,
                }}
                whileHover={
                  reduceMotion ? undefined : { scale: 1.03, borderColor: "hsl(187 80% 55% / 0.6)" }
                }
              >
                <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {m.label}
                </p>
                <p className="mt-1 font-mono text-lg font-medium text-[hsl(187_90%_78%)]">{m.value}</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">{m.hint}</p>
              </motion.div>
            ))}
          </div>

          <motion.div className="jarvis-scan-bar h-1 overflow-hidden rounded-full bg-muted">
            <motion.div
              className="h-full w-1/3 rounded-full bg-[hsl(187_90%_60%)]"
              animate={reduceMotion ? undefined : { x: ["-100%", "350%"] }}
              transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
            />
          </motion.div>
        </motion.div>
      </div>
    </motion.section>
  );
}
