"use client";

import { useMemo, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type SortDirection = "asc" | "desc";

export interface Column<T> {
  key: string;
  header: string;
  sortable?: boolean;
  className?: string;
  render: (row: T) => React.ReactNode;
  sortValue?: (row: T) => string | number;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  filterPlaceholder?: string;
  filterFn?: (row: T, query: string) => boolean;
  filterSlot?: React.ReactNode;
  emptyMessage?: string;
}

export function DataTable<T>({
  data,
  columns,
  rowKey,
  filterPlaceholder = "Filter…",
  filterFn,
  filterSlot,
  emptyMessage = "No results",
}: DataTableProps<T>) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDirection>("asc");

  const filtered = useMemo(() => {
    if (!query.trim() || !filterFn) return data;
    return data.filter((row) => filterFn(row, query.trim().toLowerCase()));
  }, [data, query, filterFn]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    const column = columns.find((c) => c.key === sortKey);
    if (!column?.sortValue) return filtered;
    return [...filtered].sort((a, b) => {
      const av = column.sortValue!(a);
      const bv = column.sortValue!(b);
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [filtered, sortKey, sortDir, columns]);

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  return (
    <div className="space-y-4">
      {(filterFn || filterSlot) && (
        <div className={filterSlot ? "filter-panel" : ""}>
          {filterSlot ? <p className="filter-panel-label mb-3">Filters</p> : null}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            {filterFn && (
              <Input
                placeholder={filterPlaceholder}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="max-w-sm bg-card"
              />
            )}
            {filterSlot}
          </div>
        </div>
      )}
      <div className="data-table-wrap overflow-x-auto">
        <table className="data-table w-full min-w-[640px] text-sm">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "px-4 py-3 text-left font-medium text-muted-foreground",
                    col.sortable && "cursor-pointer select-none hover:text-foreground",
                    col.className,
                  )}
                  onClick={col.sortable ? () => toggleSort(col.key) : undefined}
                >
                  {col.header}
                  {sortKey === col.key && (sortDir === "asc" ? " ↑" : " ↓")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-10 text-center text-muted-foreground">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              sorted.map((row) => (
                <tr key={rowKey(row)} className="border-t border-border">
                  {columns.map((col) => (
                    <td key={col.key} className={cn("px-4 py-3", col.className)}>
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge variant={statusVariant(status)}>{status.replace(/_/g, " ")}</Badge>;
}
