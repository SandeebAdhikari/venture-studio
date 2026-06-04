"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import type { DashboardSummaryResponse } from "@/types/api";

const JARVIS = 0x6ee7ff;
const JARVIS_DIM = 0x1a4a55;

function supportsWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

function studioNodes(summary: DashboardSummaryResponse) {
  const opp = summary.opportunities.total;
  const signals = summary.classification.signals_classified ?? 0;
  const ranked = summary.ranking.ranked_opportunity_count;
  const agents = (summary.agents ?? []).length;
  const max = Math.max(opp, signals, ranked, agents, 1);
  return [
    { label: "opp", weight: opp / max },
    { label: "sig", weight: signals / max },
    { label: "rank", weight: ranked / max },
    { label: "agt", weight: agents / max },
  ];
}

function mountStudioCore(
  host: HTMLDivElement,
  summary: DashboardSummaryResponse,
  reducedMotion: boolean,
  isMobile: boolean,
): () => void {
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x000000, 0.07);

  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 60);
  camera.position.set(0, 0.2, 4.8);

  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: !isMobile,
    powerPreference: "low-power",
  });
  renderer.setClearColor(0x000000, 0);
  host.appendChild(renderer.domElement);

  const root = new THREE.Group();
  scene.add(root);

  const coreGeo = new THREE.OctahedronGeometry(0.38, 0);
  const coreWire = new THREE.LineSegments(
    new THREE.EdgesGeometry(coreGeo),
    new THREE.LineBasicMaterial({ color: JARVIS, transparent: true, opacity: 0.9 }),
  );
  root.add(coreWire);

  const nodes = studioNodes(summary);
  const satellites: THREE.Mesh[] = [];
  nodes.forEach((node, i) => {
    const angle = (i / nodes.length) * Math.PI * 2;
    const radius = 1.35 + node.weight * 0.45;
    const size = 0.06 + node.weight * 0.1;
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(size, 12, 12),
      new THREE.MeshBasicMaterial({
        color: JARVIS,
        transparent: true,
        opacity: 0.55 + node.weight * 0.35,
      }),
    );
    mesh.position.set(Math.cos(angle) * radius, (i % 2 === 0 ? 0.15 : -0.15), Math.sin(angle) * radius);
    root.add(mesh);
    satellites.push(mesh);

    const link = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        mesh.position.clone(),
      ]),
      new THREE.LineBasicMaterial({
        color: JARVIS_DIM,
        transparent: true,
        opacity: 0.35,
      }),
    );
    root.add(link);
  });

  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(1.65, 0.006, 8, 128),
    new THREE.MeshBasicMaterial({ color: JARVIS_DIM, transparent: true, opacity: 0.45 }),
  );
  ring.rotation.x = Math.PI / 2.2;
  root.add(ring);

  let raf = 0;
  let running = true;
  const resize = () => {
    const w = host.clientWidth;
    const h = host.clientHeight;
    if (w < 1 || h < 1) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.25 : 1.75));
  };

  resize();
  const ro = new ResizeObserver(resize);
  ro.observe(host);

  const tick = (t: number) => {
    if (!running) return;
    raf = requestAnimationFrame(tick);
    const s = reducedMotion ? 0 : t * 0.00035;
    root.rotation.y = s;
    satellites.forEach((sat, i) => {
      if (!reducedMotion) {
        sat.position.y = (i % 2 === 0 ? 0.15 : -0.15) + Math.sin(t * 0.0012 + i) * 0.08;
      }
    });
    ring.rotation.z = s * 0.6;
    renderer.render(scene, camera);
  };
  tick(0);

  return () => {
    running = false;
    cancelAnimationFrame(raf);
    ro.disconnect();
    renderer.dispose();
    coreGeo.dispose();
    host.removeChild(renderer.domElement);
  };
}

interface DashboardJarvisCoreProps {
  summary: DashboardSummaryResponse;
  reducedMotion: boolean;
  isMobile: boolean;
}

export function DashboardJarvisCore({
  summary,
  reducedMotion,
  isMobile,
}: DashboardJarvisCoreProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [webgl, setWebgl] = useState(true);

  useEffect(() => {
    setWebgl(supportsWebGL());
  }, []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !webgl) return;
    return mountStudioCore(host, summary, reducedMotion, isMobile);
  }, [summary, reducedMotion, isMobile, webgl]);

  if (!webgl) {
    return (
      <div
        className="flex h-full min-h-[220px] items-center justify-center font-mono text-xs text-[hsl(187_70%_55%)]"
        aria-hidden
      >
        STUDIO_CORE :: STANDBY
      </div>
    );
  }

  return <div ref={hostRef} className="jarvis-core-canvas h-full min-h-[220px] w-full" />;
}
