"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { AgentJarvisHud } from "@/components/agents/agent-jarvis-hud";
import type { AgentStepSync } from "@/lib/agents/agent-step-sync";
import type { DashboardAgentStatus } from "@/types/api";

const AgentJarvisCore = dynamic(
  () => import("@/components/agents/agent-jarvis-core").then((m) => m.AgentJarvisCore),
  { ssr: false },
);

interface AgentJarvisHeroProps {
  agents: DashboardAgentStatus[];
  averageCoverage: number | null | undefined;
  stepSync: AgentStepSync;
}

export function AgentJarvisHero({ agents, averageCoverage, stepSync }: AgentJarvisHeroProps) {
  const reduceMotion = useReducedMotion();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const sync = () => setIsMobile(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  return (
    <motion.section
      className="jarvis-hero-panel relative overflow-hidden rounded-xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative grid min-h-[280px] lg:grid-cols-[1.1fr_1fr]">
        <div className="relative flex items-center justify-center p-4 lg:p-6">
          <AgentJarvisCore
            agents={agents}
            activeStep={stepSync.activeStep}
            reducedMotion={!!reduceMotion}
            isMobile={isMobile}
          />
        </div>
        <AgentJarvisHud
          agents={agents}
          averageCoverage={averageCoverage}
          stepSync={stepSync}
        />
      </div>
    </motion.section>
  );
}
