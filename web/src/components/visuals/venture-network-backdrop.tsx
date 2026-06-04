"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const SignalNetworkCanvas = dynamic(
  () =>
    import("@/components/visuals/signal-network-canvas").then((m) => m.SignalNetworkCanvas),
  { ssr: false },
);

/**
 * Atmospheric intelligence-graph backdrop. Renders nothing when WebGL is unavailable
 * or the user prefers reduced motion without a static fallback requirement — the
 * existing CSS gradient on .dashboard-canvas remains visible.
 */
export function VentureNetworkBackdrop() {
  const [ready, setReady] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const mobile = window.matchMedia("(max-width: 768px)");

    const sync = () => {
      setReducedMotion(motion.matches);
      setIsMobile(mobile.matches);
    };

    sync();
    setReady(true);

    motion.addEventListener("change", sync);
    mobile.addEventListener("change", sync);
    return () => {
      motion.removeEventListener("change", sync);
      mobile.removeEventListener("change", sync);
    };
  }, []);

  return (
    <div className="venture-network-backdrop" aria-hidden>
      {ready ? (
        <SignalNetworkCanvas reducedMotion={reducedMotion} isMobile={isMobile} />
      ) : null}
    </div>
  );
}
