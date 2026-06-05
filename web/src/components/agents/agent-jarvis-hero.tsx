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
  stepSync: AgentStepSync;
}

export function AgentJarvisHero({ agents, stepSync }: AgentJarvisHeroProps) {
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
      className="agent-jarvis-hero jarvis-hero-panel relative overflow-hidden rounded-xl border border-[hsl(187_45%_32%/0.45)]"
      initial={reduceMotion ? false : { opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
    >
      <div className="jarvis-hero-grid pointer-events-none absolute inset-0" aria-hidden />
      <div className="jarvis-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative grid lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <div className="jarvis-scene-host jarvis-scene-host--agents w-full">
          <AgentJarvisCore
            agents={agents}
            activeStep={stepSync.activeStep}
            reducedMotion={!!reduceMotion}
            isMobile={isMobile}
          />
        </div>
        <div className="flex items-center border-t border-[hsl(187_45%_32%/0.25)] lg:border-t-0">
          <AgentJarvisHud />
        </div>
      </div>
    </motion.section>
  );
}
