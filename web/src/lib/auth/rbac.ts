import type { DashboardRole } from "@/lib/auth/types";

/** Dashboard pages that require authentication. */
export const PROTECTED_PAGE_PREFIXES = [
  "/dashboard",
  "/pipeline",
  "/approvals",
  "/reports",
  "/budget",
  "/agents",
  "/opportunities",
] as const;

/** Pages allowed for read-only viewer role. */
const VIEWER_PAGE_PREFIXES = ["/dashboard", "/reports", "/budget", "/opportunities"] as const;

/** Pages requiring admin or founder (operational controls). */
const ADMIN_PAGE_PREFIXES = ["/pipeline", "/approvals", "/agents"] as const;

const MUTATING_METHODS = new Set(["POST", "PATCH", "PUT", "DELETE"]);

/** API path prefixes viewer may read (GET/HEAD). */
const VIEWER_READ_API_PREFIXES = [
  "dashboard",
  "budget",
  "reports",
  "opportunities",
  "executive-reports",
] as const;

/** Additional read prefixes for admin/founder. */
const ADMIN_READ_API_PREFIXES = [
  "approvals",
  "pipeline",
  "scheduler",
  "jobs",
  "executive-ranking",
] as const;

/** Mutations allowed for admin (not viewer). */
const ADMIN_MUTATE_PREFIXES = [
  "approvals/",
  "pipeline/",
  "scheduler/",
  "jobs/",
  "executive-ranking/",
  "executive-ranking",
] as const;

/** Destructive / platform-admin mutations — founder only. */
const FOUNDER_ONLY_MUTATE_PREFIXES = [
  "sources",
  "sources/",
  "rss-feeds",
  "rss-feeds/",
  "categories",
  "categories/",
  "complaints",
  "complaints/",
] as const;

function matchesPrefix(path: string, prefix: string): boolean {
  const normalized = prefix.endsWith("/") ? prefix.slice(0, -1) : prefix;
  return path === normalized || path.startsWith(`${normalized}/`);
}

function matchesAnyPrefix(path: string, prefixes: readonly string[]): boolean {
  return prefixes.some((prefix) => matchesPrefix(path, prefix));
}

export function isProtectedPage(pathname: string): boolean {
  return PROTECTED_PAGE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function canAccessPage(pathname: string, role: DashboardRole): boolean {
  if (!isProtectedPage(pathname)) {
    return true;
  }
  if (role === "founder") {
    return true;
  }
  if (role === "admin") {
    return (
      matchesAnyPrefix(pathname, VIEWER_PAGE_PREFIXES) ||
      ADMIN_PAGE_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))
    );
  }
  return VIEWER_PAGE_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

export function canProxyApi(method: string, apiPath: string, role: DashboardRole): boolean {
  const normalizedPath = apiPath.replace(/^\/+/, "");
  const upperMethod = method.toUpperCase();

  const isMutating = MUTATING_METHODS.has(upperMethod);

  if (role === "founder") {
    return true;
  }

  if (!isMutating) {
    if (role === "admin") {
      return (
        matchesAnyPrefix(normalizedPath, VIEWER_READ_API_PREFIXES) ||
        matchesAnyPrefix(normalizedPath, ADMIN_READ_API_PREFIXES)
      );
    }
    return matchesAnyPrefix(normalizedPath, VIEWER_READ_API_PREFIXES);
  }

  if (role === "viewer") {
    return false;
  }

  if (matchesAnyPrefix(normalizedPath, FOUNDER_ONLY_MUTATE_PREFIXES)) {
    return false;
  }

  return matchesAnyPrefix(normalizedPath, ADMIN_MUTATE_PREFIXES);
}

export function apiForbiddenDetail(role: DashboardRole, method: string, apiPath: string): string {
  if (role === "viewer" && MUTATING_METHODS.has(method.toUpperCase())) {
    return "Viewer role cannot perform mutating API operations";
  }
  return `Role '${role}' is not allowed to ${method} ${apiPath}`;
}
