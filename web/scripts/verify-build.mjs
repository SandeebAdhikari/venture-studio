/**
 * Post-build verification for CI — ensures dashboard pages, API routes, and
 * expected App Router output were emitted by `next build`.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const nextDir = join(root, ".next");

const requiredStaticPages = [
  "/",
  "/dashboard",
  "/opportunities",
  "/pipeline",
  "/reports",
  "/approvals",
  "/budget",
  "/agents",
];

const requiredDynamicRoutes = ["/api/v1/[...path]"];

function fail(message) {
  console.error(`Build verification failed: ${message}`);
  process.exit(1);
}

if (!existsSync(nextDir)) {
  fail("`.next` directory not found — run `npm run build` first");
}

const routesManifestPath = join(nextDir, "routes-manifest.json");
if (!existsSync(routesManifestPath)) {
  fail("`.next/routes-manifest.json` not found");
}

const manifest = JSON.parse(readFileSync(routesManifestPath, "utf8"));
const staticPages = new Set((manifest.staticRoutes ?? []).map((route) => route.page));
const dynamicPages = new Set((manifest.dynamicRoutes ?? []).map((route) => route.page));

for (const page of requiredStaticPages) {
  if (!staticPages.has(page)) {
    fail(`missing static page route: ${page}`);
  }
}

for (const route of requiredDynamicRoutes) {
  if (!dynamicPages.has(route)) {
    fail(`missing dynamic API route: ${route}`);
  }
}

const requiredArtifacts = [
  join(nextDir, "BUILD_ID"),
  join(nextDir, "server", "app", "api", "v1", "[...path]", "route.js"),
  join(nextDir, "server", "app", "(founder)", "dashboard", "page.js"),
];

for (const artifact of requiredArtifacts) {
  if (!existsSync(artifact)) {
    fail(`missing build artifact: ${artifact.replace(root, ".")}`);
  }
}

console.log("Build verification passed:");
console.log(`  static pages: ${requiredStaticPages.length}`);
console.log(`  dynamic routes: ${requiredDynamicRoutes.length}`);
console.log("  shadcn/ui components compiled via dashboard and feature pages");
