"use client";

import { motion, useReducedMotion } from "framer-motion";
import { formatPercent, formatUsd } from "@/lib/utils";
import type { BudgetWarning } from "@/types/api";

const R = 88;
const C = 2 * Math.PI * R;

interface BudgetJarvisGaugeProps {
  utilizationPct: number;
  budgetExceeded: boolean;
  spentUsd: number;
  budgetUsd: number;
  remainingUsd: number;
  warnings: BudgetWarning[];
}

export function BudgetJarvisGauge({
  utilizationPct,
  budgetExceeded,
  spentUsd,
  budgetUsd,
  remainingUsd,
  warnings,
}: BudgetJarvisGaugeProps) {
  const reduceMotion = useReducedMotion();
  const displayPct = Math.min(Math.max(utilizationPct, 0), 100);
  const strokeDash = (displayPct / 100) * C;
  const accent = budgetExceeded ? "hsl(0 72% 58%)" : "hsl(187 90% 58%)";
  const glow = budgetExceeded ? "hsl(0 70% 50% / 0.45)" : "hsl(187 90% 55% / 0.45)";

  return (
    <div className="budget-jarvis-gauge flex flex-col items-center">
      <div className="relative">
        <svg
          className="budget-gauge-svg -rotate-90"
          width={220}
          height={220}
          viewBox="0 0 220 220"
          aria-hidden
        >
          <circle
            cx="110"
            cy="110"
            r={R}
            fill="none"
            stroke="hsl(187 25% 18% / 0.8)"
            strokeWidth="10"
          />
          {warnings.map((w) => {
            const angle = (w.threshold_pct / 100) * 360 - 90;
            const rad = (angle * Math.PI) / 180;
            const x2 = 110 + (R + 4) * Math.cos(rad);
            const y2 = 110 + (R + 4) * Math.sin(rad);
            const x1 = 110 + (R - 8) * Math.cos(rad);
            const y1 = 110 + (R - 8) * Math.sin(rad);
            return (
              <line
                key={w.threshold_pct}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={w.triggered ? "hsl(0 70% 55% / 0.9)" : "hsl(187 40% 35% / 0.6)"}
                strokeWidth="2"
              />
            );
          })}
          <motion.circle
            cx="110"
            cy="110"
            r={R}
            fill="none"
            stroke={accent}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${strokeDash} ${C}`}
            initial={reduceMotion ? false : { strokeDasharray: `0 ${C}` }}
            animate={{ strokeDasharray: `${strokeDash} ${C}` }}
            transition={{ duration: 0.9, ease: "easeOut" }}
            style={{ filter: `drop-shadow(0 0 12px ${glow})` }}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-muted-foreground">
            Utilization
          </p>
          <p
            className={`mt-1 font-mono text-4xl font-bold tabular-nums ${
              budgetExceeded ? "text-destructive" : "text-[hsl(187_92%_78%)]"
            }`}
          >
            {formatPercent(displayPct)}
          </p>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            {budgetExceeded ? "limit exceeded" : "within budget"}
          </p>
        </div>
      </div>

      <div className="mt-6 w-full max-w-[220px] space-y-2">
        <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
          <span>Spent</span>
          <span className={budgetExceeded ? "text-destructive" : "text-[hsl(187_85%_72%)]"}>
            {formatUsd(spentUsd, 4)}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-muted/80">
          <motion.div
            className={`h-full rounded-full ${budgetExceeded ? "bg-destructive" : "jarvis-score-fill"}`}
            initial={reduceMotion ? false : { width: 0 }}
            animate={{ width: `${displayPct}%` }}
            transition={{ duration: 0.8 }}
          />
        </div>
        <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
          <span>Budget {formatUsd(budgetUsd)}</span>
          <span>Left {formatUsd(remainingUsd, 4)}</span>
        </div>
      </div>
    </div>
  );
}
