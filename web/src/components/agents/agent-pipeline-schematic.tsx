"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { PipelineAgent } from "@/lib/agents/pipeline-order";
import { PIPELINE_PHASES } from "@/lib/agents/pipeline-order";

export function AgentPipelineSchematic({ agents }: { agents: PipelineAgent[] }) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="jarvis-pipeline-schematic mb-10 hidden lg:block" aria-hidden>
      <div className="relative mb-3 flex min-h-[1.25rem] items-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-[hsl(187_70%_55%)]">
          Execution map
        </p>
        <p className="pointer-events-none absolute left-1/2 -translate-x-1/2 font-mono text-[10px] text-muted-foreground">
          Start → Finish
        </p>
      </div>

      <div className="relative flex items-center">
        <div className="jarvis-schematic-track absolute left-6 right-6 top-1/2 h-px -translate-y-1/2" />
        {!reduceMotion && (
          <motion.div
            className="jarvis-schematic-pulse absolute top-1/2 h-1 w-8 -translate-y-1/2 rounded-full bg-[hsl(187_90%_60%)]"
            animate={{ left: ["4%", "92%"] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
          />
        )}

        {PIPELINE_PHASES.map((phase, phaseIndex) => {
          const phaseAgents = agents.filter(
            (a) => a.step >= phase.stepRange[0] && a.step <= phase.stepRange[1],
          );
          return (
            <div
              key={phase.id}
              className="relative z-10 flex flex-1 flex-col items-center gap-3"
            >
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                {phase.title}
              </p>
              <div className="flex items-center gap-2">
                {phaseAgents.map((agent) => (
                  <div
                    key={agent.agent}
                    className="jarvis-schematic-node flex h-9 w-9 items-center justify-center rounded-full border border-[hsl(187_55%_45%/0.6)] bg-card font-mono text-[10px] font-medium text-[hsl(187_85%_72%)]"
                    title={agent.display_name}
                  >
                    {agent.step}
                  </div>
                ))}
              </div>
              {phaseIndex < PIPELINE_PHASES.length - 1 && (
                <span className="absolute -right-3 top-[calc(50%+8px)] font-mono text-[hsl(187_80%_55%)]">
                  →
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
