"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardOpportunitiesResponse } from "@/types/api";

interface OpportunityJarvisHeroProps {
  ranking: DashboardOpportunitiesResponse | undefined;
  visibleCount: number;
  inventoryTotal?: number;
}

export function OpportunityJarvisHero({
  ranking,
  visibleCount,
  inventoryTotal,
}: OpportunityJarvisHeroProps) {
  const reduceMotion = useReducedMotion();

  const metrics = [
    {
      label: "Ranked pool",
      value: ranking ? String(ranking.ranked_opportunity_count) : "—",
    },
    {
      label: "Total ventures",
      value: ranking ? String(ranking.total_opportunities) : String(inventoryTotal ?? "—"),
    },
    {
      label: "Showing",
      value: String(visibleCount),
    },
    {
      label: "Ranking ver",
      value: ranking?.version != null ? `v${ranking.version}` : "—",
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
            Venture opportunity matrix
          </motion.p>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            Executive intelligence board
          </h2>
          <p className="max-w-xl text-sm text-muted-foreground">
            Ranked ventures and full inventory from dashboard opportunities and the opportunities
            API — filters apply client-side on loaded data.
          </p>
          {ranking && (
            <p className="font-mono text-[10px] uppercase tracking-widest text-[hsl(187_65%_50%)]">
              Source · {ranking.source.replace(/_/g, " ")} · top {ranking.top_n}
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:max-w-lg">
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
