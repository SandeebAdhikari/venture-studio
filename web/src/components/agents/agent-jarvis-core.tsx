"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import {
  createJarvisRenderer,
  JARVIS,
  JARVIS_DIM,
  setRendererSize,
  supportsWebGL,
} from "@/lib/visuals/jarvis-three";
import {
  addGlowMesh,
  addOrbitalRing,
  addWireframeShell,
  bindVisibilityLoop,
  createEdgePulses,
  createGridFloor,
  createPulsePoints,
  disposeGrid,
  disposeResources,
  type SceneDisposable,
  updateEdgePulsePositions,
} from "@/lib/visuals/jarvis-scene-utils";
import type { DashboardAgentStatus } from "@/types/api";

const SCENE_RADIUS = 2.05;
const RING_A = 1.72;
const RING_B = 1.28;
const SCENE_SCALE = 1.28;

function agentSuccessRate(agent: DashboardAgentStatus): number {
  if (agent.current_total <= 0) return 0;
  return agent.current_completed / agent.current_total;
}

function mountAgentMesh(
  host: HTMLDivElement,
  agents: DashboardAgentStatus[],
  activeStep: number | null,
  reducedMotion: boolean,
  isMobile: boolean,
): () => void {
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x000000, 0.046);

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 80);
  const renderer = createJarvisRenderer(host, isMobile);
  const disposables: SceneDisposable[] = [];

  const root = new THREE.Group();
  root.rotation.x = 0.32;
  root.scale.setScalar(SCENE_SCALE);
  scene.add(root);

  const grid = createGridFloor(5.5, 14, JARVIS_DIM, -0.75);
  root.add(grid);

  const orchestrator = new THREE.Group();
  orchestrator.position.y = 0.05;
  root.add(orchestrator);

  const hubGeo = new THREE.IcosahedronGeometry(0.18, 0);
  addWireframeShell(orchestrator, hubGeo, JARVIS, 0.95, disposables);
  addGlowMesh(orchestrator, hubGeo, JARVIS, 0.15, disposables);
  addOrbitalRing(orchestrator, 0.32, 0.004, Math.PI / 2, 0, JARVIS_DIM, 0.5, disposables);

  const count = Math.max(agents.length, 8);
  const nodeGroups: THREE.Group[] = [];
  const nodePositions: THREE.Vector3[] = [];
  const pulseEdges: Array<{ from: THREE.Vector3; to: THREE.Vector3 }> = [];

  agents.forEach((agent, i) => {
    const rate = agentSuccessRate(agent);
    const step = i + 1;
    const isActive = activeStep === step;
    const angle = (i / count) * Math.PI * 2 - Math.PI / 2;
    const ring = i % 2 === 0 ? RING_A : RING_B;
    const y = i % 2 === 0 ? 0.28 : -0.22;
    const x = Math.cos(angle) * ring;
    const z = Math.sin(angle) * ring;
    const pos = new THREE.Vector3(x, y, z);
    nodePositions.push(pos);

    const group = new THREE.Group();
    group.position.copy(pos);
    root.add(group);
    nodeGroups.push(group);

    const size = 0.11 + rate * 0.05 + (isActive ? 0.05 : 0);
    const nodeGeo = new THREE.OctahedronGeometry(size, 0);
    addWireframeShell(group, nodeGeo, isActive ? 0xffffff : JARVIS, isActive ? 1 : 0.55 + rate * 0.4, disposables);
    addGlowMesh(group, nodeGeo, JARVIS, isActive ? 0.35 : 0.08 + rate * 0.12, disposables);

    if (isActive) {
      const halo = addOrbitalRing(group, size * 1.6, 0.004, Math.PI / 2, 0, JARVIS, 0.75, disposables);
      halo.userData.isHalo = true;
      const beam = new THREE.Mesh(
        new THREE.CylinderGeometry(0.015, 0.015, 0.55, 6),
        new THREE.MeshBasicMaterial({ color: JARVIS, transparent: true, opacity: 0.7 }),
      );
      beam.position.y = size + 0.28;
      group.add(beam);
      disposables.push({ geometry: beam.geometry, material: beam.material as THREE.Material });
    }

    const link = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), pos.clone().sub(orchestrator.position)]),
      new THREE.LineBasicMaterial({
        color: JARVIS,
        transparent: true,
        opacity: isActive ? 0.7 : 0.12 + rate * 0.28,
      }),
    );
    orchestrator.add(link);
    disposables.push({ geometry: link.geometry, material: link.material as THREE.Material });
    pulseEdges.push({ from: pos, to: orchestrator.position });
  });

  for (let i = 0; i < nodePositions.length; i += 1) {
    const curr = nodePositions[i];
    const next = nodePositions[(i + 1) % nodePositions.length];
    const step = i + 1;
    const isActive = activeStep === step;
    const seg = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([curr, next]),
      new THREE.LineBasicMaterial({
        color: JARVIS,
        transparent: true,
        opacity: isActive ? 0.8 : 0.22,
      }),
    );
    root.add(seg);
    disposables.push({ geometry: seg.geometry, material: seg.material as THREE.Material });
    pulseEdges.push({ from: curr, to: next });
  }

  for (let i = 0; i < nodePositions.length; i += 2) {
    const a = nodePositions[i];
    const b = nodePositions[(i + 4) % nodePositions.length];
    const cross = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([a, b]),
      new THREE.LineBasicMaterial({ color: JARVIS_DIM, transparent: true, opacity: 0.14 }),
    );
    root.add(cross);
    disposables.push({ geometry: cross.geometry, material: cross.material as THREE.Material });
  }

  const trackA = addOrbitalRing(root, RING_A, 0.006, Math.PI / 2, 0, JARVIS_DIM, 0.4, disposables);
  trackA.position.y = 0.28;
  const trackB = addOrbitalRing(root, RING_B, 0.006, Math.PI / 2, 0, JARVIS_DIM, 0.35, disposables);
  trackB.position.y = -0.22;

  const pulseCount = isMobile ? 6 : 10;
  const { geo: pulseGeo, mat: pulseMat, mesh: pulseMesh } = createPulsePoints(
    pulseCount,
    JARVIS,
    isMobile,
  );
  root.add(pulseMesh);
  const pulses = createEdgePulses(pulseEdges, pulseCount);
  const pulsePos = pulseGeo.attributes.position.array as Float32Array;

  const resize = () =>
    setRendererSize(renderer, host, camera, isMobile, SCENE_RADIUS, 0.9);
  const ro = new ResizeObserver(resize);
  ro.observe(host);
  resize();

  let t0 = performance.now();
  const stopLoop = bindVisibilityLoop(reducedMotion, (now, delta) => {
    const elapsed = (now - t0) / 1000;
    if (!reducedMotion) {
      root.rotation.y = elapsed * 0.08;
      orchestrator.rotation.y = elapsed * 0.25;
      nodeGroups.forEach((group, i) => {
        const step = i + 1;
        const isActive = activeStep === step;
        const bob = Math.sin(elapsed * 1.3 + i * 0.7) * 0.03;
        group.position.y = (i % 2 === 0 ? 0.28 : -0.22) + bob;
        if (isActive) {
          group.rotation.y = elapsed * 0.6;
          group.children.forEach((child) => {
            if (child.userData.isHalo) {
              child.rotation.z = elapsed * 1.2;
            }
          });
        }
      });
      updateEdgePulsePositions(pulses, pulsePos, delta, reducedMotion);
      pulseGeo.attributes.position.needsUpdate = true;
    }
    renderer.render(scene, camera);
  });

  return () => {
    stopLoop();
    ro.disconnect();
    renderer.dispose();
    disposeResources(disposables);
    disposeGrid(grid);
    pulseGeo.dispose();
    pulseMat.dispose();
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
  const [webgl, setWebgl] = useState(true);

  useEffect(() => {
    setWebgl(supportsWebGL());
  }, []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !webgl) return;

    let dispose: (() => void) | undefined;
    try {
      dispose = mountAgentMesh(host, agents, activeStep, reducedMotion, isMobile);
    } catch {
      return;
    }
    return () => dispose?.();
  }, [agents, activeStep, reducedMotion, isMobile, webgl]);

  if (!webgl) {
    return (
      <div className="jarvis-scene-fallback font-mono text-xs text-[hsl(187_70%_55%)]">
        AGENT_MESH :: STANDBY
      </div>
    );
  }

  return <div ref={hostRef} className="jarvis-scene-canvas h-full w-full" />;
}
