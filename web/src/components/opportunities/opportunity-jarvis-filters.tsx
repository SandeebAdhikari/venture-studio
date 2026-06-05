"use client";

import { Select } from "@/components/ui/input";

interface OpportunityJarvisFiltersProps {
  source: "ranking" | "all";
  reviewFilter: string;
  searchQuery: string;
  onSourceChange: (source: "ranking" | "all") => void;
  onReviewChange: (status: string) => void;
  onSearchChange: (query: string) => void;
}

export function OpportunityJarvisFilters({
  source,
  reviewFilter,
  searchQuery,
  onSourceChange,
  onReviewChange,
  onSearchChange,
}: OpportunityJarvisFiltersProps) {
  return (
    <div className="jarvis-panel rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.55)] p-5 sm:p-6">
      <p className="mb-4 font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
        Query controls
      </p>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
        <label className="flex min-w-0 flex-1 flex-col gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            Data source
          </span>
          <Select
            value={source}
            onChange={(e) => onSourceChange(e.target.value as "ranking" | "all")}
            className="max-w-none"
          >
            <option value="ranking">Executive ranking</option>
            <option value="all">All opportunities</option>
          </Select>
        </label>
        <label className="flex min-w-0 flex-1 flex-col gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            Review status
          </span>
          <Select
            value={reviewFilter}
            onChange={(e) => onReviewChange(e.target.value)}
            className="max-w-none"
          >
            <option value="">All review statuses</option>
            <option value="new">New</option>
            <option value="reviewing">Reviewing</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="archived">Archived</option>
          </Select>
        </label>
        <label className="flex min-w-0 flex-[1.2] flex-col gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            Search title
          </span>
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Filter by title…"
            className="flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
      </div>
    </div>
  );
}
