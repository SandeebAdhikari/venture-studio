import * as THREE from "three";
import { JARVIS, JARVIS_DIM } from "./jarvis-three";

export type EdgePulse = {
  from: THREE.Vector3;
  to: THREE.Vector3;
  t: number;
  speed: number;
};

export type SceneDisposable = {
  geometry?: THREE.BufferGeometry;
  material?: THREE.Material | THREE.Material[];
};

export function createEdgePulses(
  edges: Array<{ from: THREE.Vector3; to: THREE.Vector3 }>,
  count: number,
): EdgePulse[] {
  return Array.from({ length: count }, (_, i) => ({
    from: edges[i % edges.length].from,
    to: edges[i % edges.length].to,
    t: Math.random(),
    speed: 0.28 + Math.random() * 0.22,
  }));
}

export function updateEdgePulsePositions(
  pulses: EdgePulse[],
  positions: Float32Array,
  delta: number,
  reducedMotion: boolean,
): void {
  const tmp = new THREE.Vector3();
  pulses.forEach((pulse, i) => {
    if (!reducedMotion) {
      pulse.t += pulse.speed * delta;
      if (pulse.t > 1) pulse.t -= 1;
    }
    tmp.copy(pulse.from).lerp(pulse.to, pulse.t);
    positions[i * 3] = tmp.x;
    positions[i * 3 + 1] = tmp.y;
    positions[i * 3 + 2] = tmp.z;
  });
}

export function createPulsePoints(
  count: number,
  color: number,
  isMobile: boolean,
): { geo: THREE.BufferGeometry; mat: THREE.PointsMaterial; mesh: THREE.Points } {
  const positions = new Float32Array(count * 3);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    color,
    size: isMobile ? 0.07 : 0.055,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.92,
    depthWrite: false,
  });
  return { geo, mat, mesh: new THREE.Points(geo, mat) };
}

export function createGridFloor(
  size: number,
  divisions: number,
  color: number,
  y = 0,
): THREE.GridHelper {
  const grid = new THREE.GridHelper(size, divisions, color, color);
  (grid.material as THREE.Material).opacity = 0.11;
  (grid.material as THREE.Material).transparent = true;
  grid.position.y = y;
  return grid;
}

export function addWireframeShell(
  parent: THREE.Object3D,
  geometry: THREE.BufferGeometry,
  color: number,
  opacity: number,
  disposables: SceneDisposable[],
): THREE.LineSegments {
  const wire = new THREE.LineSegments(
    new THREE.EdgesGeometry(geometry),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity }),
  );
  parent.add(wire);
  disposables.push({ geometry: wire.geometry, material: wire.material as THREE.Material });
  return wire;
}

export function addGlowMesh(
  parent: THREE.Object3D,
  geometry: THREE.BufferGeometry,
  color: number,
  opacity: number,
  disposables: SceneDisposable[],
): THREE.Mesh {
  const mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      depthWrite: false,
    }),
  );
  parent.add(mesh);
  disposables.push({ geometry, material: mesh.material as THREE.Material });
  return mesh;
}

export function addOrbitalRing(
  parent: THREE.Object3D,
  radius: number,
  tube: number,
  tiltX: number,
  tiltZ: number,
  color: number,
  opacity: number,
  disposables: SceneDisposable[],
): THREE.Mesh {
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(radius, tube, 8, 96),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity }),
  );
  ring.rotation.set(tiltX, 0, tiltZ);
  parent.add(ring);
  disposables.push({ geometry: ring.geometry, material: ring.material as THREE.Material });
  return ring;
}

/** Partial ring arc — used for gauges and metric readouts. */
export function addArcRing(
  parent: THREE.Object3D,
  radius: number,
  tube: number,
  startRad: number,
  spanRad: number,
  color: number,
  opacity: number,
  disposables: SceneDisposable[],
): THREE.Mesh {
  const arc = new THREE.Mesh(
    new THREE.TorusGeometry(radius, tube, 6, 64, spanRad),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity }),
  );
  arc.rotation.x = Math.PI / 2;
  arc.rotation.z = startRad;
  parent.add(arc);
  disposables.push({ geometry: arc.geometry, material: arc.material as THREE.Material });
  return arc;
}

export function addScanSweep(
  parent: THREE.Object3D,
  radius: number,
  disposables: SceneDisposable[],
): THREE.Mesh {
  const sweep = new THREE.Mesh(
    new THREE.RingGeometry(radius * 0.08, radius, 48, 1, 0, Math.PI / 2.8),
    new THREE.MeshBasicMaterial({
      color: JARVIS,
      transparent: true,
      opacity: 0.14,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  sweep.rotation.x = -Math.PI / 2;
  parent.add(sweep);
  disposables.push({ geometry: sweep.geometry, material: sweep.material as THREE.Material });
  return sweep;
}

export function addLatitudeRings(
  parent: THREE.Object3D,
  radius: number,
  count: number,
  disposables: SceneDisposable[],
): THREE.Mesh[] {
  const rings: THREE.Mesh[] = [];
  for (let i = 0; i < count; i += 1) {
    const t = i / (count - 1);
    const y = (t - 0.5) * radius * 1.6;
    const r = Math.sqrt(Math.max(radius * radius - y * y, 0.01));
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(r, 0.004, 6, 48),
      new THREE.MeshBasicMaterial({ color: JARVIS_DIM, transparent: true, opacity: 0.35 }),
    );
    ring.rotation.x = Math.PI / 2;
    ring.position.y = y;
    parent.add(ring);
    rings.push(ring);
    disposables.push({ geometry: ring.geometry, material: ring.material as THREE.Material });
  }
  return rings;
}

export function bindVisibilityLoop(
  reducedMotion: boolean,
  tick: (now: number, delta: number) => void,
): () => void {
  let raf = 0;
  let last = performance.now();

  const frame = (now: number) => {
    raf = requestAnimationFrame(frame);
    if (document.visibilityState === "hidden") return;
    const delta = Math.min((now - last) / 1000, 0.05);
    last = now;
    tick(now, delta);
  };

  if (reducedMotion) {
    tick(performance.now(), 0);
  } else {
    raf = requestAnimationFrame(frame);
  }

  const onVisibility = () => {
    if (document.visibilityState === "hidden") {
      cancelAnimationFrame(raf);
      raf = 0;
    } else if (!reducedMotion && raf === 0) {
      last = performance.now();
      raf = requestAnimationFrame(frame);
    }
  };
  document.addEventListener("visibilitychange", onVisibility);

  return () => {
    document.removeEventListener("visibilitychange", onVisibility);
    cancelAnimationFrame(raf);
  };
}

export function disposeResources(resources: SceneDisposable[]): void {
  const disposedGeometries = new Set<THREE.BufferGeometry>();
  const disposedMaterials = new Set<THREE.Material>();

  resources.forEach(({ geometry, material }) => {
    if (geometry && !disposedGeometries.has(geometry)) {
      geometry.dispose();
      disposedGeometries.add(geometry);
    }
    if (Array.isArray(material)) {
      material.forEach((m) => {
        if (!disposedMaterials.has(m)) {
          m.dispose();
          disposedMaterials.add(m);
        }
      });
    } else if (material && !disposedMaterials.has(material)) {
      material.dispose();
      disposedMaterials.add(material);
    }
  });
}

export function disposeGrid(grid: THREE.GridHelper): void {
  grid.geometry.dispose();
  (grid.material as THREE.Material).dispose();
}
