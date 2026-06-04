"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

type NetworkGraph = {
  positions: Float32Array;
  edges: Array<{ from: number; to: number }>;
};

type Pulse = {
  edgeIndex: number;
  t: number;
  speed: number;
};

function hslVarToColor(cssValue: string): THREE.Color {
  const parts = cssValue.trim().split(/\s+/);
  const h = (parseFloat(parts[0]) || 0) / 360;
  const s = (parseFloat(parts[1]) || 0) / 100;
  const l = (parseFloat(parts[2]) || 50) / 100;
  return new THREE.Color().setHSL(h, s, l);
}

function applyThemeMaterials(
  nodeMat: THREE.PointsMaterial,
  hubMat: THREE.PointsMaterial,
  lineMat: THREE.LineBasicMaterial,
  pulseMat: THREE.PointsMaterial,
) {
  const styles = getComputedStyle(document.documentElement);
  const fg = styles.getPropertyValue("--foreground").trim() || "0 0% 98%";
  const border = styles.getPropertyValue("--border").trim() || "0 0% 18%";

  nodeMat.color = hslVarToColor(fg);
  nodeMat.opacity = 0.5;
  hubMat.color = hslVarToColor(fg);
  hubMat.opacity = 0.92;
  lineMat.color = hslVarToColor(border);
  lineMat.opacity = 0.38;
  pulseMat.color = hslVarToColor(fg);
  pulseMat.opacity = 1;
}

function buildGraph(nodeCount: number): NetworkGraph {
  const positions = new Float32Array(nodeCount * 3);
  const nodes: THREE.Vector3[] = [];

  nodes.push(new THREE.Vector3(0, 0, 0));
  positions[0] = 0;
  positions[1] = 0;
  positions[2] = 0;

  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 1; i < nodeCount; i += 1) {
    const t = i / (nodeCount - 1);
    const radius = 2.4 + t * 1.6;
    const theta = golden * i;
    const y = (1 - t * 2) * 1.1;
    const x = Math.cos(theta) * radius;
    const z = Math.sin(theta) * radius;
    nodes.push(new THREE.Vector3(x, y, z));
    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;
  }

  const edges: Array<{ from: number; to: number }> = [];
  const edgeKeys = new Set<string>();

  const addEdge = (from: number, to: number) => {
    if (from === to) return;
    const key = from < to ? `${from}-${to}` : `${to}-${from}`;
    if (edgeKeys.has(key)) return;
    edgeKeys.add(key);
    edges.push({ from, to });
  };

  for (let i = 1; i < nodeCount; i += 1) {
    addEdge(0, i);
  }

  for (let i = 1; i < nodeCount; i += 1) {
    const dist: Array<{ j: number; d: number }> = [];
    for (let j = 1; j < nodeCount; j += 1) {
      if (i === j) continue;
      dist.push({ j, d: nodes[i].distanceTo(nodes[j]) });
    }
    dist.sort((a, b) => a.d - b.d);
    addEdge(i, dist[0].j);
    if (dist[1]) addEdge(i, dist[1].j);
  }

  return { positions, edges };
}

function supportsWebGL(): boolean {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return !!(
      canvas.getContext("webgl2") ??
      canvas.getContext("webgl") ??
      canvas.getContext("experimental-webgl")
    );
  } catch {
    return false;
  }
}

function mountNetworkScene(
  host: HTMLDivElement,
  reducedMotion: boolean,
  isMobile: boolean,
): () => void {
  const nodeCount = isMobile ? 12 : 18;
  const graph = buildGraph(nodeCount);
  const pulses: Pulse[] = graph.edges.slice(0, isMobile ? 3 : 5).map((_, i) => ({
    edgeIndex: i % graph.edges.length,
    t: Math.random(),
    speed: 0.06 + Math.random() * 0.05,
  }));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.set(0, 0.5, 7.5);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: !isMobile,
    powerPreference: "low-power",
  });
  renderer.setClearColor(0x000000, 0);
  host.appendChild(renderer.domElement);

  const group = new THREE.Group();
  scene.add(group);

  const hubPos = new Float32Array(3);
  const satellitePos = new Float32Array((nodeCount - 1) * 3);
  satellitePos.set(graph.positions.subarray(3));

  const hubGeo = new THREE.BufferGeometry();
  hubGeo.setAttribute("position", new THREE.BufferAttribute(hubPos, 3));
  const satelliteGeo = new THREE.BufferGeometry();
  satelliteGeo.setAttribute("position", new THREE.BufferAttribute(satellitePos, 3));

  const nodeMat = new THREE.PointsMaterial({
    size: isMobile ? 0.07 : 0.055,
    sizeAttenuation: true,
    transparent: true,
    depthWrite: false,
  });
  const hubMat = new THREE.PointsMaterial({
    size: isMobile ? 0.14 : 0.12,
    sizeAttenuation: true,
    transparent: true,
    depthWrite: false,
  });
  const lineMat = new THREE.LineBasicMaterial({
    transparent: true,
    depthWrite: false,
  });
  const pulseMat = new THREE.PointsMaterial({
    size: isMobile ? 0.09 : 0.07,
    sizeAttenuation: true,
    transparent: true,
    depthWrite: false,
  });

  applyThemeMaterials(nodeMat, hubMat, lineMat, pulseMat);

  group.add(new THREE.Points(satelliteGeo, nodeMat));
  group.add(new THREE.Points(hubGeo, hubMat));

  const linePositions = new Float32Array(graph.edges.length * 6);
  graph.edges.forEach((edge, i) => {
    const a = edge.from * 3;
    const b = edge.to * 3;
    const o = i * 6;
    linePositions[o] = graph.positions[a];
    linePositions[o + 1] = graph.positions[a + 1];
    linePositions[o + 2] = graph.positions[a + 2];
    linePositions[o + 3] = graph.positions[b];
    linePositions[o + 4] = graph.positions[b + 1];
    linePositions[o + 5] = graph.positions[b + 2];
  });

  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute("position", new THREE.BufferAttribute(linePositions, 3));
  group.add(new THREE.LineSegments(lineGeo, lineMat));

  const pulsePos = new Float32Array(pulses.length * 3);
  const pulseGeo = new THREE.BufferGeometry();
  pulseGeo.setAttribute("position", new THREE.BufferAttribute(pulsePos, 3));
  group.add(new THREE.Points(pulseGeo, pulseMat));

  const tmpA = new THREE.Vector3();
  const tmpB = new THREE.Vector3();

  const updatePulsePositions = (delta: number) => {
    pulses.forEach((pulse, i) => {
      if (!reducedMotion) {
        pulse.t += pulse.speed * delta;
        if (pulse.t > 1) pulse.t -= 1;
      }
      const edge = graph.edges[pulse.edgeIndex];
      tmpA.set(
        graph.positions[edge.from * 3],
        graph.positions[edge.from * 3 + 1],
        graph.positions[edge.from * 3 + 2],
      );
      tmpB.set(
        graph.positions[edge.to * 3],
        graph.positions[edge.to * 3 + 1],
        graph.positions[edge.to * 3 + 2],
      );
      tmpA.lerp(tmpB, pulse.t);
      pulsePos[i * 3] = tmpA.x;
      pulsePos[i * 3 + 1] = tmpA.y;
      pulsePos[i * 3 + 2] = tmpA.z;
    });
    pulseGeo.attributes.position.needsUpdate = true;
  };

  const resize = () => {
    const width = host.clientWidth;
    const height = host.clientHeight;
    if (width === 0 || height === 0) return;
    const dpr = Math.min(window.devicePixelRatio || 1, isMobile ? 1 : 1.5);
    renderer.setPixelRatio(dpr);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host);
  resize();

  let raf = 0;
  let last = performance.now();

  const renderFrame = (time: number) => {
    const delta = Math.min((time - last) / 1000, 0.05);
    last = time;

    if (!reducedMotion) {
      group.rotation.y += delta * 0.08;
      group.rotation.x = Math.sin(time * 0.00015) * 0.06;
      updatePulsePositions(delta);
    }

    renderer.render(scene, camera);
  };

  const loop = (time: number) => {
    raf = requestAnimationFrame(loop);
    if (document.visibilityState === "hidden") return;
    renderFrame(time);
  };

  if (reducedMotion) {
    updatePulsePositions(0);
    renderFrame(performance.now());
  } else {
    raf = requestAnimationFrame(loop);
  }

  const onVisibility = () => {
    if (document.visibilityState === "hidden") {
      cancelAnimationFrame(raf);
      raf = 0;
    } else if (!reducedMotion && raf === 0) {
      last = performance.now();
      raf = requestAnimationFrame(loop);
    }
  };

  const themeObserver = new MutationObserver(() => {
    applyThemeMaterials(nodeMat, hubMat, lineMat, pulseMat);
  });
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });

  document.addEventListener("visibilitychange", onVisibility);

  return () => {
    document.removeEventListener("visibilitychange", onVisibility);
    themeObserver.disconnect();
    resizeObserver.disconnect();
    cancelAnimationFrame(raf);
    renderer.dispose();
    hubGeo.dispose();
    satelliteGeo.dispose();
    lineGeo.dispose();
    pulseGeo.dispose();
    nodeMat.dispose();
    hubMat.dispose();
    lineMat.dispose();
    pulseMat.dispose();
    if (renderer.domElement.parentElement === host) {
      host.removeChild(renderer.domElement);
    }
  };
}

interface SignalNetworkCanvasProps {
  reducedMotion: boolean;
  isMobile: boolean;
}

export function SignalNetworkCanvas({ reducedMotion, isMobile }: SignalNetworkCanvasProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !supportsWebGL()) return;

    let dispose: (() => void) | undefined;
    try {
      dispose = mountNetworkScene(host, reducedMotion, isMobile);
    } catch {
      return;
    }

    return () => {
      dispose?.();
    };
  }, [reducedMotion, isMobile]);

  return <div ref={hostRef} className="h-full w-full" />;
}
