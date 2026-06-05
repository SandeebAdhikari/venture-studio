"use client";

import { motion, useReducedMotion } from "framer-motion";
import { AgentPipelineSchematic } from "@/components/agents/agent-pipeline-schematic";
import { Badge } from "@/components/ui/badge";
import { truncateText } from "@/lib/pipeline/stage-sync";
import type { AgentStepSync } from "@/lib/agents/agent-step-sync";
import {
  agentsForPhase,
  PIPELINE_PHASES,
  sortAgentsByPipeline,
  type PipelineAgent,
} from "@/lib/agents/pipeline-order";
import type { DashboardAgentStatus } from "@/types/api";

const AGENT_NAME_MAX = 24;

function successRate(agent: DashboardAgentStatus): number {
  if (agent.current_total <= 0) return 0;
  return Math.round((agent.current_completed / agent.current_total) * 100);
}

function statusLabel(agent: PipelineAgent, rate: number, isExecuting: boolean): string {
  if (isExecuting) return "Executing";
  if (agent.current_failed > 0) return "Needs attention";
  if (rate >= 80) return "Optimal";
  if (agent.current_total === 0) return "Awaiting runs";
  return "Active";
}

function AgentNodeCard({
  agent,
  isLastInPhase,
  reduceMotion,
  isExecuting,
}: {
  agent: PipelineAgent;
  isLastInPhase: boolean;
  reduceMotion: boolean;
  isExecuting: boolean;
}) {
  const rate = successRate(agent);
  const status = statusLabel(agent, rate, isExecuting);
  const displayName = truncateText(agent.display_name, AGENT_NAME_MAX);

  return (
    <div className="jarvis-pipeline-node flex gap-4">
      <div className="flex w-12 shrink-0 flex-col items-center">
        <motion.div
          className={`jarvis-node-badge relative z-10 flex h-12 w-12 items-center justify-center rounded-full border bg-card font-mono text-sm font-semibold shadow-[0_0_20px_hsl(187_80%_50%/0.2)] ${
            isExecuting
              ? "jarvis-stage-node--running jarvis-stage-node--process border-[hsl(187_90%_60%/0.85)] text-[hsl(187_95%_85%)]"
              : "border-[hsl(187_70%_50%/0.55)] text-[hsl(187_90%_75%)]"
          }`}
          initial={reduceMotion ? false : { scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 22 }}
        >
          {String(agent.step).padStart(2, "0")}
          {isExecuting && !reduceMotion && (
            <span className="jarvis-stage-ping absolute inset-0 rounded-full" aria-hidden />
          )}
        </motion.div>
        {!isLastInPhase && <div className="jarvis-node-connector mt-2 min-h-[2.5rem] w-px flex-1" />}
      </div>

      <motion.article
        className={`jarvis-agent-card relative mb-6 flex h-[11.5rem] min-h-[11.5rem] min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border bg-gradient-to-br from-card/95 to-card/70 p-5 backdrop-blur-md ${
          isExecuting
            ? "border-[hsl(187_55%_50%/0.7)] shadow-[0_0_28px_hsl(187_90%_55%/0.18)]"
            : "border-[hsl(187_35%_30%/0.45)]"
        }`}
        initial={reduceMotion ? false : { opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ type: "spring", stiffness: 280, damping: 26, delay: agent.step * 0.04 }}
        whileHover={
          reduceMotion
            ? undefined
            : {
                y: -4,
                boxShadow: "0 12px 40px hsl(187 80% 45% / 0.12), 0 0 0 1px hsl(187 70% 55% / 0.25)",
              }
        }
      >
        <div className="flex min-h-0 items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p
              className={`font-mono text-[10px] uppercase tracking-[0.2em] ${
                isExecuting ? "text-[hsl(187_90%_70%)]" : "text-[hsl(187_65%_52%)]"
              }`}
            >
              {status}
            </p>
            <h3
              className="mt-1 truncate text-base font-semibold leading-tight tracking-tight text-foreground"
              title={agent.display_name}
            >
              {displayName}
            </h3>
          </div>
          <div className="shrink-0 text-right">
            <p className="font-mono text-2xl font-light tabular-nums text-[hsl(187_90%_78%)]">
              {isExecuting ? "···" : `${rate}%`}
            </p>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              {isExecuting ? "live" : "success"}
            </p>
          </div>
        </div>

        <div className="mt-auto flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={isExecuting ? "default" : agent.current_failed > 0 ? "warning" : "success"}>
              {isExecuting ? "In flight" : `${agent.current_total} runs`}
            </Badge>
            <span className="truncate font-mono text-xs text-muted-foreground">
              {agent.current_completed} done · {agent.current_skipped} skip · {agent.current_failed} fail
            </span>
          </div>

          <div className="h-1 overflow-hidden rounded-full bg-muted/80">
            {isExecuting && !reduceMotion ? (
              <motion.div
                className="jarvis-score-fill h-full rounded-full"
                animate={{ width: ["15%", "70%", "15%"], opacity: [0.7, 1, 0.7] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
              />
            ) : (
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-[hsl(187_50%_38%)] via-[hsl(187_85%_62%)] to-[hsl(187_95%_78%)]"
                initial={{ width: 0 }}
                animate={{ width: `${rate}%` }}
                transition={{ type: "spring", stiffness: 70, damping: 18, delay: 0.1 }}
              />
            )}
          </div>
        </div>
      </motion.article>
    </div>
  );
}

function PhaseColumn({
  phase,
  agents,
  reduceMotion,
  index,
  activeStep,
}: {
  phase: (typeof PIPELINE_PHASES)[number];
  agents: PipelineAgent[];
  reduceMotion: boolean;
  index: number;
  activeStep: number | null;
}) {
  return (
    <motion.section
      className="jarvis-phase-column relative flex flex-col"
      initial={reduceMotion ? false : { opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.12, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="jarvis-phase-header mb-6 rounded-xl border border-[hsl(187_40%_35%/0.35)] bg-[hsl(187_30%_12%/0.4)] px-4 py-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-[hsl(187_75%_58%)]">
          Phase {index + 1}
        </p>
        <h3 className="mt-1 text-base font-semibold text-foreground">{phase.title}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{phase.subtitle}</p>
      </div>

      {agents.length === 0 ? (
        <p className="text-sm text-muted-foreground">No agents in this phase.</p>
      ) : (
        agents.map((agent, i) => (
          <AgentNodeCard
            key={agent.agent}
            agent={agent}
            isLastInPhase={i === agents.length - 1}
            reduceMotion={reduceMotion}
            isExecuting={activeStep === agent.step}
          />
        ))
      )}

      {index < PIPELINE_PHASES.length - 1 && (
        <div
          className="jarvis-phase-arrow pointer-events-none absolute -right-4 top-1/2 hidden -translate-y-1/2 font-mono text-xl text-[hsl(187_80%_55%/0.7)] xl:block"
          aria-hidden
        >
          →
        </div>
      )}
    </motion.section>
  );
}

interface AgentActivityGridProps {
  agents: DashboardAgentStatus[] | null | undefined;
  stepSync: AgentStepSync;
}

export function AgentActivityGrid({
  agents,
  stepSync,
}: AgentActivityGridProps) {
  const reduceMotion = useReducedMotion();
  const sorted = sortAgentsByPipeline(agents ?? []);
  const activeStep = stepSync.activeStep;

  if (sorted.length === 0) {
    return (
      <p className="font-mono text-sm text-muted-foreground">
        {"// No agent telemetry in current cycle."}
      </p>
    );
  }

  return (
    <div className="jarvis-pipeline-panel rounded-2xl border border-[hsl(187_35%_28%/0.4)] bg-[hsl(var(--card)/0.6)] p-6 sm:p-8 lg:p-10">
      <div className="mb-8 max-w-2xl">
        <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_70%_55%)]">
          Research pipeline
          {stepSync.isLive && (
            <span className="ml-2 text-[hsl(187_85%_65%)]">· synced with orchestrator</span>
          )}
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
          How intelligence flows through your agents
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Each opportunity moves left to right in three phases. Numbers show strict
          execution order — the same sequence the backend orchestrator uses.
        </p>
      </div>

      <AgentPipelineSchematic stepSync={stepSync} />

      <div className="grid gap-12 xl:grid-cols-3 xl:gap-6">
        {PIPELINE_PHASES.map((phase, index) => (
          <PhaseColumn
            key={phase.id}
            phase={phase}
            agents={agentsForPhase(sorted, phase.stepRange)}
            reduceMotion={!!reduceMotion}
            index={index}
            activeStep={activeStep}
          />
        ))}
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-6 border-t border-border/60 pt-6 font-mono text-[10px] uppercase tracking-widest text-muted-foreground lg:hidden">
        <span>Discover</span>
        <span className="text-[hsl(187_70%_55%)]">→</span>
        <span>Validate</span>
        <span className="text-[hsl(187_70%_55%)]">→</span>
        <span>Strategize</span>
      </div>
    </div>
  );
}

export function AgentCompactList({ agents }: { agents: DashboardAgentStatus[] | null | undefined }) {
  const list = agents ?? [];
  return (
    <div className="space-y-2">
      {list.map((agent) => (
        <div
          key={agent.agent}
          className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-4 py-3 text-sm"
        >
          <span className="truncate font-medium">{truncateText(agent.display_name, 28)}</span>
          <span className="font-mono text-xs text-muted-foreground">{agent.current_completed}</span>
        </div>
      ))}
    </div>
  );
}
