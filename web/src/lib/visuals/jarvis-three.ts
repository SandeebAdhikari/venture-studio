import * as THREE from "three";

export const JARVIS = 0x6ee7ff;
export const JARVIS_DIM = 0x1a4a55;
export const JARVIS_ALERT = 0xff5c6a;

export function supportsWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

/** Pull camera back so the scene bounding radius fits width and height. */
export function fitPerspectiveCamera(
  camera: THREE.PerspectiveCamera,
  width: number,
  height: number,
  radius: number,
  padding = 1.18,
): void {
  if (width < 1 || height < 1) return;
  camera.aspect = width / height;
  const fovRad = (camera.fov * Math.PI) / 180;
  const distV = radius / Math.tan(fovRad / 2);
  const distH = radius / (Math.tan(fovRad / 2) * camera.aspect);
  const distance = Math.max(distV, distH) * padding;
  camera.position.set(0, 0.12, distance);
  camera.lookAt(0, 0, 0);
  camera.updateProjectionMatrix();
}

export function createJarvisRenderer(host: HTMLDivElement, isMobile: boolean): THREE.WebGLRenderer {
  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: !isMobile,
    powerPreference: "low-power",
  });
  renderer.setClearColor(0x000000, 0);
  host.appendChild(renderer.domElement);
  return renderer;
}

export function setRendererSize(
  renderer: THREE.WebGLRenderer,
  host: HTMLDivElement,
  camera: THREE.PerspectiveCamera,
  isMobile: boolean,
  sceneRadius: number,
  padding = 1.18,
): void {
  const w = host.clientWidth;
  const h = host.clientHeight;
  if (w < 1 || h < 1) return;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, isMobile ? 1.25 : 2));
  renderer.setSize(w, h, false);
  fitPerspectiveCamera(camera, w, h, sceneRadius, padding);
}
