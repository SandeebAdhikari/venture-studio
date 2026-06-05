"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { DashboardReportsResponse } from "@/types/api";

interface ReportsJarvisMetricsProps {
  data: DashboardReportsResponse;
  libraryCount: number;
}

export function ReportsJarvisMetrics({ data, libraryCount }: ReportsJarvisMetricsProps) {
  const reduceMotion = useReducedMotion();
  const typeEntries = Object.entries(data.total_by_type ?? {});
  const ventureCount =
    data.total_by_type?.venture_recommendation ?? data.venture_reports.length;
  const topOppCount =
    data.total_by_type?.top_opportunities ?? data.top_opportunity_reports.length;
  const pipelineCount =
    data.total_by_type?.pipeline_summary ?? data.pipeline_reports.length;

  const metrics = [
    { label: "In library", value: String(libraryCount) },
    { label: "Venture reports", value: String(ventureCount) },
    { label: "Top opportunities", value: String(topOppCount) },
    { label: "Pipeline summaries", value: String(pipelineCount) },
  ];

  return (
    <div className="space-y-4">
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
            transition={{ delay: 0.1 + i * 0.05 }}
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

      {data.featured_venture_report && (
        <motion.div
          className="jarvis-hud-metric rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-[hsl(var(--card)/0.55)] px-4 py-3"
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            Featured report
          </p>
          <p className="mt-1 truncate text-sm font-medium text-foreground">
            {data.featured_venture_report.title}
          </p>
        </motion.div>
      )}

      {typeEntries.length > 0 && (
        <div className="flex flex-wrap gap-2">
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
  );
}
