"use client";

import { useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import { Select } from "@/components/ui/input";
import { formatDate } from "@/lib/utils";
import type { ApprovalRequestRead } from "@/types/api";

interface ApprovalsJarvisQueueProps {
  items: ApprovalRequestRead[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  statusFilter: string;
  subjectFilter: string;
  onStatusFilterChange: (v: string) => void;
  onSubjectFilterChange: (v: string) => void;
}

export function ApprovalsJarvisQueue({
  items,
  selectedId,
  onSelect,
  statusFilter,
  subjectFilter,
  onStatusFilterChange,
  onSubjectFilterChange,
}: ApprovalsJarvisQueueProps) {
  const reduceMotion = useReducedMotion();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((a) => a.title.toLowerCase().includes(q));
  }, [items, search]);

  return (
    <div className="jarvis-panel flex max-h-[40rem] flex-col rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-5 sm:p-6">
      <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
        Request queue
      </p>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <Select
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value)}
          className="max-w-none flex-1"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="research_requested">Research requested</option>
        </Select>
        <Select
          value={subjectFilter}
          onChange={(e) => onSubjectFilterChange(e.target.value)}
          className="max-w-none flex-1"
        >
          <option value="">All subjects</option>
          <option value="executive_ranking">Executive ranking</option>
          <option value="venture_report">Venture report</option>
        </Select>
      </div>

      <input
        type="search"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Filter by title…"
        className="mt-2 flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm"
      />

      <ul className="mt-4 flex-1 space-y-2 overflow-y-auto">
        {filtered.length === 0 ? (
          <li className="py-8 text-center text-sm text-muted-foreground">
            No approval requests match your filters.
          </li>
        ) : (
          filtered.map((item, i) => {
            const isActive = item.id === selectedId;
            const isPending = item.status === "pending";
            return (
              <li key={item.id}>
                <motion.button
                  type="button"
                  onClick={() => onSelect(item.id)}
                  className={`jarvis-stage-index-row w-full rounded-lg px-3 py-3 text-left ${
                    isActive ? "jarvis-stage-index-row--active" : ""
                  }`}
                  initial={reduceMotion ? false : { opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.02 }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="line-clamp-2 text-sm font-medium text-foreground">{item.title}</p>
                    {isPending && (
                      <span className="jarvis-status-pill jarvis-status-pill--active shrink-0 rounded-full px-2 py-0.5 font-mono text-[9px] uppercase">
                        open
                      </span>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <StatusBadge status={item.status} />
                    <span className="font-mono text-[9px] uppercase text-muted-foreground">
                      {item.subject_type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                    {formatDate(item.updated_at)}
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
