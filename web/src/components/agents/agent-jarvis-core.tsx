"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { DashboardAgentStatus } from "@/types/api";

const JARVIS = 0x6ee7ff;
const JARVIS_DIM = 0x1a4a55;

function agentSuccessRate(agent: DashboardAgentStatus): number {
  if (agent.current_total <= 0) return 0;
  return agent.current_completed / agent.current_total;
}

function supportsWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

function mountJarvisCore(
  host: HTMLDivElement,
  agents: DashboardAgentStatus[],
  activeStep: number | null,
  reducedMotion: boolean,
  isMobile: boolean,
): () => void {
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x000000, 0.08);

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 80);
  camera.position.set(0, 0.35, 5.2);

  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: !isMobile,
    powerPreference: "low-power",
  });
  renderer.setClearColor(0x000000, 0);
  host.appendChild(renderer.domElement);

  const root = new THREE.Group();
  scene.add(root);

  const coreGeo = new THREE.IcosahedronGeometry(0.42, 1);
  const coreWire = new THREE.LineSegments(
    new THREE.WireframeGeometry(coreGeo),
    new THREE.LineBasicMaterial({ color: JARVIS, transparent: true, opacity: 0.85 }),
  );
  root.add(coreWire);

  const coreMesh = new THREE.Mesh(
    coreGeo,
    new THREE.MeshBasicMaterial({
      color: JARVIS,
      transparent: true,
      opacity: 0.12,
      wireframe: false,
    }),
  );
  root.add(coreMesh);

  const rings: THREE.Mesh[] = [];
  [1.05, 1.45, 1.9].forEach((radius, i) => {
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(radius, 0.008, 8, 96),
      new THREE.MeshBasicMaterial({
        color: i === 1 ? JARVIS : JARVIS_DIM,
        transparent: true,
        opacity: 0.35 + i * 0.12,
      }),
    );
    ring.rotation.x = Math.PI / 2 + i * 0.35;
    ring.rotation.y = i * 0.5;
    root.add(ring);
    rings.push(ring);
  });

  const scanMat = new THREE.MeshBasicMaterial({
    color: JARVIS,
    transparent: true,
    opacity: 0.45,
    side: THREE.DoubleSide,
  });
  const scanRing = new THREE.Mesh(new THREE.RingGeometry(2.1, 2.12, 64), scanMat);
  scanRing.rotation.x = -Math.PI / 2;
  scanRing.visible = false;
  root.add(scanRing);

  const agentGroup = new THREE.Group();
  root.add(agentGroup);

  const agentNodes: THREE.Mesh[] = [];
  const agentLines: THREE.Line[] = [];
  const count = Math.max(agents.length, 1);

  agents.forEach((agent, i) => {
    const rate = agentSuccessRate(agent);
    const step = i + 1;
    const isActive = activeStep === step;
    const angle = (i / count) * Math.PI * 2;
    const orbit = 2.35 + rate * 0.45;
    const y = Math.sin(angle * 2) * 0.35;
    const x = Math.cos(angle) * orbit;
    const z = Math.sin(angle) * orbit;

    const node = new THREE.Mesh(
      new THREE.SphereGeometry(0.06 + rate * 0.04 + (isActive ? 0.03 : 0), 12, 12),
      new THREE.MeshBasicMaterial({
        color: isActive ? 0xffffff : JARVIS,
        transparent: true,
        opacity: isActive ? 0.95 : 0.55 + rate * 0.45,
      }),
    );
    node.position.set(x, y, z);
    agentGroup.add(node);
    agentNodes.push(node);

    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(x, y, z),
    ]);
    const line = new THREE.Line(
      lineGeo,
      new THREE.LineBasicMaterial({
        color: JARVIS,
        transparent: true,
        opacity: isActive ? 0.75 : 0.15 + rate * 0.35,
      }),
    );
    agentGroup.add(line);
    agentLines.push(line);
  });

  const particleCount = isMobile ? 120 : 220;
  const particlePos = new Float32Array(particleCount * 3);
  for (let i = 0; i < particleCount; i += 1) {
    const r = 2.8 + Math.random() * 1.2;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    particlePos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    particlePos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.4;
    particlePos[i * 3 + 2] = r * Math.cos(phi);
  }
  const particleGeo = new THREE.BufferGeometry();
  particleGeo.setAttribute("position", new THREE.BufferAttribute(particlePos, 3));
  const particles = new THREE.Points(
    particleGeo,
    new THREE.PointsMaterial({
      color: JARVIS,
      size: isMobile ? 0.02 : 0.015,
      transparent: true,
      opacity: 0.5,
      depthWrite: false,
    }),
  );
  root.add(particles);

  const resize = () => {
    const w = host.clientWidth;
    const h = host.clientHeight;
    if (w === 0 || h === 0) return;
    const dpr = Math.min(window.devicePixelRatio || 1, isMobile ? 1 : 1.75);
    renderer.setPixelRatio(dpr);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host);
  resize();

  let raf = 0;
  let t0 = performance.now();

  const tick = (now: number) => {
    raf = requestAnimationFrame(tick);
    if (document.visibilityState === "hidden") return;

    const elapsed = (now - t0) / 1000;

    if (!reducedMotion) {
      root.rotation.y = elapsed * 0.18;
      coreMesh.rotation.x = elapsed * 0.35;
      coreMesh.rotation.z = elapsed * 0.22;
      rings.forEach((ring, i) => {
        ring.rotation.z += 0.004 * (i % 2 === 0 ? 1 : -1);
      });

      agentNodes.forEach((node, i) => {
        const step = i + 1;
        const isActive = activeStep === step;
        const pulse = isActive ? 1 + Math.sin(elapsed * 4) * 0.18 : 1 + Math.sin(elapsed * 2 + i) * 0.06;
        node.scale.setScalar(pulse);
      });

      particles.rotation.y = elapsed * 0.05;
    }

    renderer.render(scene, camera);
  };

  if (reducedMotion) {
    renderer.render(scene, camera);
  } else {
    raf = requestAnimationFrame(tick);
  }

  const onVisibility = () => {
    if (document.visibilityState === "hidden") {
      cancelAnimationFrame(raf);
      raf = 0;
    } else if (!reducedMotion && raf === 0) {
      t0 = performance.now();
      raf = requestAnimationFrame(tick);
    }
  };
  document.addEventListener("visibilitychange", onVisibility);

  return () => {
    document.removeEventListener("visibilitychange", onVisibility);
    resizeObserver.disconnect();
    cancelAnimationFrame(raf);
    renderer.dispose();
    coreGeo.dispose();
    coreWire.geometry.dispose();
    (coreWire.material as THREE.Material).dispose();
    (coreMesh.material as THREE.Material).dispose();
    rings.forEach((r) => {
      r.geometry.dispose();
      (r.material as THREE.Material).dispose();
    });
    scanRing.geometry.dispose();
    scanMat.dispose();
    agentNodes.forEach((n) => {
      n.geometry.dispose();
      (n.material as THREE.Material).dispose();
    });
    agentLines.forEach((l) => {
      l.geometry.dispose();
      (l.material as THREE.Material).dispose();
    });
    particleGeo.dispose();
    (particles.material as THREE.Material).dispose();
    if (renderer.domElement.parentElement === host) {
      host.removeChild(renderer.domElement);
    }
  };
}

interface AgentJarvisCoreProps {
  agents: DashboardAgentStatus[];
  activeStep?: number | null;
  reducedMotion?: boolean;
  isMobile?: boolean;
}

export function AgentJarvisCore({
  agents,
  activeStep = null,
  reducedMotion = false,
  isMobile = false,
}: AgentJarvisCoreProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !supportsWebGL()) return;

    let dispose: (() => void) | undefined;
    try {
      dispose = mountJarvisCore(host, agents, activeStep, reducedMotion, isMobile);
    } catch {
      return;
    }
    return () => dispose?.();
  }, [agents, activeStep, reducedMotion, isMobile]);

  return <div ref={hostRef} className="jarvis-core-canvas h-full min-h-[220px] w-full" />;
}
