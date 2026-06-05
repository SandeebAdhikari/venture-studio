"use client";

import { motion, useReducedMotion } from "framer-motion";

export function ReportsJarvisHero() {
  const reduceMotion = useReducedMotion();

  return (
    <motion.section
      className="jarvis-hero-panel relative overflow-hidden rounded-xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative space-y-2 p-6 sm:p-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_80%_65%)]">
          Intelligence archive
        </p>
        <h2 className="text-xl font-semibold text-foreground">Report command center</h2>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Venture recommendations, rankings, and pipeline summaries from dashboard reports.
        </p>
      </div>
    </motion.section>
  );
}
