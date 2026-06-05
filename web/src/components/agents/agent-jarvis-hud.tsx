"use client";

import { motion, useReducedMotion } from "framer-motion";

export function AgentJarvisHud() {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className="jarvis-hud flex flex-col justify-center px-6 py-5 sm:px-8 sm:py-6 lg:py-5 lg:pl-4 lg:pr-8"
      initial={reduceMotion ? false : { opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 120, damping: 18, delay: 0.15 }}
    >
      <div className="space-y-1">
        <motion.p
          className="jarvis-hud-label font-mono text-[10px] uppercase tracking-[0.35em] text-[hsl(187_80%_65%)]"
          animate={reduceMotion ? undefined : { opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2.4, repeat: Infinity }}
        >
          Intelligence mesh online
        </motion.p>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          Research agent constellation
        </h2>
        <p className="text-sm text-muted-foreground">
          Dual-ring agent mesh — eight autonomous nodes coordinated through a central orchestrator.
        </p>
      </div>
    </motion.div>
  );
}
