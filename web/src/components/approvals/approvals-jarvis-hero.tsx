"use client";

import { motion, useReducedMotion } from "framer-motion";

export function ApprovalsJarvisHero() {
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
          Governance console
        </p>
        <h2 className="text-xl font-semibold text-foreground">Approval command</h2>
        <p className="text-sm text-muted-foreground">
          Review founder requests for executive rankings and venture reports.
        </p>
      </div>
    </motion.section>
  );
}
