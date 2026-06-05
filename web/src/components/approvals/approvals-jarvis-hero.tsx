"use client";

import { motion, useReducedMotion } from "framer-motion";

interface ApprovalsJarvisHeroProps {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

export function ApprovalsJarvisHero({
  total,
  pending,
  approved,
  rejected,
}: ApprovalsJarvisHeroProps) {
  const reduceMotion = useReducedMotion();

  const metrics = [
    { label: "Total", value: String(total) },
    { label: "Pending", value: String(pending) },
    { label: "Approved", value: String(approved) },
    { label: "Rejected", value: String(rejected) },
  ];

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
          Governance console
        </p>
        <h2 className="mt-1 text-xl font-semibold text-foreground">Approval command</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Review founder requests for executive rankings and venture reports.
        </p>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              className="jarvis-hud-metric rounded-lg border border-[hsl(187_50%_40%/0.35)] bg-black/20 px-3 py-2.5"
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * i }}
            >
              <p className="font-mono text-[10px] uppercase text-muted-foreground">{m.label}</p>
              <p className="mt-1 font-mono text-lg text-[hsl(187_90%_78%)]">{m.value}</p>
            </motion.div>
          ))}
        </div>

        {pending > 0 && (
          <p className="mt-4 font-mono text-xs text-[hsl(187_75%_58%)]">
            &gt; {pending} request{pending === 1 ? "" : "s"} awaiting decision
          </p>
        )}
      </div>
    </motion.section>
  );
}
