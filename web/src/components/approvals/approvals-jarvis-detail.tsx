"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ApprovalActions } from "@/components/approvals/approval-actions";
import { StatusBadge } from "@/components/shared/data-table";
import { formatDate } from "@/lib/utils";
import type { ApprovalRequestRead } from "@/types/api";

interface ApprovalsJarvisDetailProps {
  approval: ApprovalRequestRead | null;
  onComplete: () => void;
}

export function ApprovalsJarvisDetail({ approval, onComplete }: ApprovalsJarvisDetailProps) {
  const reduceMotion = useReducedMotion();

  if (!approval) {
    return (
      <div className="jarvis-panel flex min-h-[20rem] items-center justify-center rounded-2xl border border-dashed border-[hsl(187_35%_28%/0.45)] p-8 text-center">
        <p className="text-sm text-muted-foreground">Select an approval request from the queue.</p>
      </div>
    );
  }

  return (
    <motion.div
      key={approval.id}
      className="jarvis-stage-lens space-y-5 rounded-2xl border border-[hsl(187_40%_32%/0.45)] bg-gradient-to-br from-[hsl(187_26%_11%/0.55)] to-transparent p-6"
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_75%_58%)]">
          Decision lens
        </p>
        <h3 className="mt-1 text-lg font-semibold text-foreground">{approval.title}</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          <StatusBadge status={approval.status} />
          <StatusBadge status={approval.subject_type} />
        </div>
        <p className="mt-2 font-mono text-xs text-muted-foreground">
          Updated {formatDate(approval.updated_at)}
        </p>
      </div>

      <ApprovalActions approval={approval} onComplete={onComplete} />

      {approval.decisions.length > 0 && (
        <div className="space-y-2 border-t border-border/50 pt-4">
          <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            Comment history
          </p>
          {approval.decisions.map((d) => (
            <div
              key={d.id}
              className="rounded-lg border border-[hsl(187_35%_28%/0.35)] bg-black/15 px-3 py-3 text-sm"
            >
              <p className="font-medium capitalize">{d.decision_type.replace(/_/g, " ")}</p>
              {d.comment && <p className="mt-1 text-muted-foreground">{d.comment}</p>}
              <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                {d.actor} · {formatDate(d.created_at)}
              </p>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
