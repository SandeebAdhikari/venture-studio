"use client";

import { useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { StatusBadge } from "@/components/shared/data-table";
import type { OpportunityRead } from "@/types/api";

interface OpportunityJarvisInventoryProps {
  items: OpportunityRead[];
  emptyMessage: string;
}

export function OpportunityJarvisInventory({ items, emptyMessage }: OpportunityJarvisInventoryProps) {
  const reduceMotion = useReducedMotion();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const active = useMemo(
    () => items.find((i) => i.id === selectedId) ?? items[0] ?? null,
    [items, selectedId],
  );

  if (items.length === 0) {
    return (
      <p className="jarvis-panel rounded-2xl border border-[hsl(187_35%_28%/0.4)] p-8 text-center text-sm text-muted-foreground">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
      <ul className="jarvis-panel max-h-[32rem] space-y-2 overflow-y-auto rounded-2xl border border-[hsl(187_35%_28%/0.4)] p-4 sm:p-5">
        <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.35em] text-muted-foreground">
          Inventory ({items.length})
        </p>
        {items.map((item) => {
          const isActive = active?.id === item.id;
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => setSelectedId(item.id)}
                className={`jarvis-stage-index-row w-full rounded-lg px-3 py-3 text-left ${
                  isActive ? "jarvis-stage-index-row--active" : ""
                }`}
              >
                <p className="truncate text-sm font-medium text-foreground">{item.title}</p>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <StatusBadge status={item.review_status} />
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {Math.round(item.confidence_score * 100)}% conf
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      {active && (
        <motion.article
          key={active.id}
          className="jarvis-stage-lens jarvis-opp-lens rounded-2xl border border-[hsl(187_40%_32%/0.45)] bg-gradient-to-br from-[hsl(187_26%_11%/0.55)] to-transparent p-6"
          initial={reduceMotion ? false : { opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
            Venture dossier
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">{active.title}</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            <StatusBadge status={active.review_status} />
            <span className="font-mono text-xs text-muted-foreground">{active.llm_model}</span>
          </div>

          <dl className="mt-6 space-y-4 text-sm">
            {[
              { label: "Problem", value: active.problem_statement },
              { label: "Target user", value: active.target_user },
              { label: "Gap", value: active.gap },
              { label: "Alternatives", value: active.existing_alternatives },
            ].map((field) => (
              <div key={field.label}>
                <dt className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {field.label}
                </dt>
                <dd className="mt-1 leading-relaxed text-foreground/90">{field.value || "—"}</dd>
              </div>
            ))}
          </dl>

          <p className="mt-6 font-mono text-[10px] text-muted-foreground">
            Confidence {Math.round(active.confidence_score * 100)}% · Updated{" "}
            {new Date(active.updated_at).toLocaleDateString()}
          </p>
        </motion.article>
      )}
    </div>
  );
}
