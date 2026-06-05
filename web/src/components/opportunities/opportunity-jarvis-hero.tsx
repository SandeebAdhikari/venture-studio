"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardOpportunitiesResponse } from "@/types/api";

interface OpportunityJarvisHeroProps {
  ranking: DashboardOpportunitiesResponse | undefined;
}

export function OpportunityJarvisHero({ ranking }: OpportunityJarvisHeroProps) {
  const reduceMotion = useReducedMotion();

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
          Venture opportunity matrix
        </motion.p>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          Executive intelligence board
        </h2>
        <p className="max-w-xl text-sm text-muted-foreground">
          Ranked ventures and full inventory from dashboard opportunities and the opportunities API
          — filters apply client-side on loaded data.
        </p>
        {ranking && (
          <p className="font-mono text-[10px] uppercase tracking-widest text-[hsl(187_65%_50%)]">
            Source · {ranking.source.replace(/_/g, " ")} · top {ranking.top_n}
          </p>
        )}
      </div>
    </motion.section>
  );
}
