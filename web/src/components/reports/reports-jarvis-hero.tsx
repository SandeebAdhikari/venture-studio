"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardReportsResponse } from "@/types/api";

interface ReportsJarvisHeroProps {
  data: DashboardReportsResponse;
  libraryCount: number;
}

export function ReportsJarvisHero({ data, libraryCount }: ReportsJarvisHeroProps) {
  const reduceMotion = useReducedMotion();
  const typeEntries = Object.entries(data.total_by_type ?? {});

  return (
    <motion.section
      className="jarvis-hero-panel relative overflow-hidden rounded-xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative p-6 sm:p-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_80%_65%)]">
          Intelligence archive
        </p>
        <h2 className="mt-1 text-xl font-semibold text-foreground">Report command center</h2>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Venture recommendations, rankings, and pipeline summaries from dashboard reports.
        </p>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="jarvis-hud-metric rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-black/20 px-3 py-2.5">
            <p className="font-mono text-[10px] uppercase text-muted-foreground">In library</p>
            <p className="mt-1 font-mono text-lg text-[hsl(187_90%_78%)]">{libraryCount}</p>
          </div>
          {data.featured_venture_report && (
            <div className="jarvis-hud-metric rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-black/20 px-3 py-2.5 sm:col-span-2">
              <p className="font-mono text-[10px] uppercase text-muted-foreground">Featured</p>
              <p className="mt-1 truncate text-sm font-medium text-foreground">
                {data.featured_venture_report.title}
              </p>
            </div>
          )}
        </div>

        {typeEntries.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {typeEntries.map(([type, count]) => (
              <span
                key={type}
                className="rounded-full border border-[hsl(187_40%_35%/0.4)] px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-[hsl(187_75%_60%)]"
              >
                {type.replace(/_/g, " ")} · {count}
              </span>
            ))}
          </div>
        )}
      </div>
    </motion.section>
  );
}
