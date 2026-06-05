"use client";

import { useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import { formatReportType } from "@/lib/reports/report-utils";
import { formatDate } from "@/lib/utils";
import type { DashboardReportSummary } from "@/types/api";

interface ReportsJarvisLibraryProps {
  reports: DashboardReportSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  typeFilter: string;
  onTypeFilterChange: (value: string) => void;
}

export function ReportsJarvisLibrary({
  reports,
  selectedId,
  onSelect,
  typeFilter,
  onTypeFilterChange,
}: ReportsJarvisLibraryProps) {
  const reduceMotion = useReducedMotion();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    let list = reports;
    if (typeFilter) list = list.filter((r) => r.report_type === typeFilter);
    const q = search.trim().toLowerCase();
    if (q) list = list.filter((r) => r.title.toLowerCase().includes(q));
    return list;
  }, [reports, typeFilter, search]);

  return (
    <div className="jarvis-panel flex h-full max-h-[36rem] flex-col rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-5 sm:p-6">
      <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
        Report library
      </p>

      <div className="mt-4 space-y-3">
        <select
          value={typeFilter}
          onChange={(e) => onTypeFilterChange(e.target.value)}
          className="flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm"
        >
          <option value="">All report types</option>
          <option value="venture_recommendation">Venture recommendation</option>
          <option value="top_opportunities">Top opportunities</option>
          <option value="pipeline_summary">Pipeline summary</option>
          <option value="opportunity_brief">Opportunity brief</option>
        </select>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search reports…"
          className="flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm"
        />
      </div>

      <ul className="mt-4 flex-1 space-y-2 overflow-y-auto">
        {filtered.length === 0 ? (
          <li className="py-8 text-center text-sm text-muted-foreground">No reports match.</li>
        ) : (
          filtered.map((report, i) => {
            const isActive = report.id === selectedId;
            return (
              <li key={report.id}>
                <motion.button
                  type="button"
                  onClick={() => onSelect(report.id)}
                  className={`jarvis-stage-index-row w-full rounded-lg px-3 py-3 text-left ${
                    isActive ? "jarvis-stage-index-row--active" : ""
                  }`}
                  initial={reduceMotion ? false : { opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.02 }}
                >
                  <p className="line-clamp-2 text-sm font-medium text-foreground">{report.title}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-[hsl(187_70%_55%)]">
                      {formatReportType(report.report_type)}
                    </span>
                    <StatusBadge status={report.status} />
                  </div>
                  <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                    {formatDate(report.created_at)}
                  </p>
                </motion.button>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
}
