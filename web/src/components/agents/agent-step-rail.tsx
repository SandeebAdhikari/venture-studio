"use client";

import { type CSSProperties } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { PIPELINE_PHASES } from "@/lib/agents/pipeline-order";
import type { AgentStepState, AgentStepSync } from "@/lib/agents/agent-step-sync";

function nodeClass(state: AgentStepState, isActive: boolean): string {
  if (isActive || state === "running") {
    return "jarvis-stage-node--running jarvis-stage-node--process";
  }
  switch (state) {
    case "completed":
      return "jarvis-stage-node--completed";
    case "failed":
      return "jarvis-stage-node--failed";
    case "skipped":
      return "jarvis-stage-node--skipped";
    default:
      return "jarvis-stage-node--pending";
  }
}

interface AgentStepRailProps {
  sync: AgentStepSync;
  variant?: "compact" | "wide";
  showPhaseLabels?: boolean;
  title?: string;
}

export function AgentStepRail({
  sync,
  variant = "wide",
  showPhaseLabels = true,
  title,
}: AgentStepRailProps) {
  const reduceMotion = useReducedMotion();
  const steps = Array.from({ length: 8 }, (_, i) => i + 1);
  const fillPct =
    sync.activeStep != null
      ? ((sync.activeStep - 0.5) / 8) * 100
      : (sync.completedCount / 8) * 100;

  const nodeSize = variant === "compact" ? "h-7 w-7 text-[9px]" : "h-9 w-9 text-[10px]";

  return (
    <div className="agent-step-rail">
      {(title || sync.isLive) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {title && (
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-[hsl(187_70%_55%)]">
              {title}
            </p>
          )}
          {sync.isLive && sync.activeStep != null && (
            <span className="font-mono text-[9px] uppercase tracking-wider text-[hsl(187_85%_65%)]">
              Agent {sync.activeStep} executing
            </span>
          )}
        </div>
      )}

      {showPhaseLabels && variant === "wide" && (
        <div className="mb-2 grid grid-cols-3 gap-2 text-center font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
          {PIPELINE_PHASES.map((phase) => (
            <span key={phase.id}>{phase.title}</span>
          ))}
        </div>
      )}

      <div
        className="relative rounded-lg border border-[hsl(187_35%_28%/0.35)] bg-[hsl(187_22%_8%/0.35)] px-3 py-4"
        style={{ "--agent-steps": 8, "--step-fill": `${fillPct}%` } as CSSProperties}
      >
        <div className="agent-step-rail-grid relative">
          <div className="agent-step-rail-track pointer-events-none absolute inset-x-0 top-1/2 z-0 h-px -translate-y-1/2" />
          <div
            className="agent-step-rail-track-fill pointer-events-none absolute top-1/2 z-0 h-0.5 -translate-y-1/2"
            aria-hidden
          />

          {steps.map((step) => {
            const state = sync.steps[step] ?? "pending";
            const isActive = sync.activeStep === step;
            return (
              <div key={step} className="relative z-10 flex flex-col items-center gap-1.5">
                <div
                  className={`jarvis-stage-node relative flex shrink-0 items-center justify-center rounded-full border font-mono font-semibold ${nodeSize} ${nodeClass(state, isActive)}`}
                >
                  {step}
                  {isActive && !reduceMotion && (
                    <span className="jarvis-stage-ping absolute inset-0 rounded-full" aria-hidden />
                  )}
                </div>
                {variant === "wide" && (
                  <span className="font-mono text-[8px] uppercase text-muted-foreground">
                    {state === "running" ? "live" : state === "completed" ? "done" : "—"}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
