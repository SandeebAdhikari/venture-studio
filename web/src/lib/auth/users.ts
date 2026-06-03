import type { DashboardRole, DashboardUser } from "@/lib/auth/types";
import { hashPassword, verifyPassword } from "@/lib/auth/password";

const VALID_ROLES: DashboardRole[] = ["founder", "admin", "viewer"];

interface RawDashboardUser {
  username: string;
  role: string;
  password?: string;
  passwordHash?: string;
}

let cachedUsers: DashboardUser[] | null = null;

function parseUsersJson(raw: string): RawDashboardUser[] {
  const parsed = JSON.parse(raw) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error("DASHBOARD_USERS must be a JSON array");
  }
  return parsed as RawDashboardUser[];
}

async function normalizeUser(entry: RawDashboardUser): Promise<DashboardUser> {
  if (!entry.username || typeof entry.username !== "string") {
    throw new Error("Each dashboard user requires a username");
  }
  if (!VALID_ROLES.includes(entry.role as DashboardRole)) {
    throw new Error(`Invalid role for user ${entry.username}: ${entry.role}`);
  }
  let passwordHash = entry.passwordHash;
  if (!passwordHash && entry.password) {
    passwordHash = await hashPassword(entry.password);
  }
  if (!passwordHash) {
    throw new Error(`User ${entry.username} requires password or passwordHash`);
  }
  return {
    username: entry.username,
    role: entry.role as DashboardRole,
    passwordHash,
  };
}

export async function loadDashboardUsers(): Promise<DashboardUser[]> {
  if (cachedUsers) {
    return cachedUsers;
  }
  const raw = process.env.DASHBOARD_USERS;
  if (!raw?.trim()) {
    throw new Error("DASHBOARD_USERS is not configured");
  }
  const entries = parseUsersJson(raw);
  if (entries.length === 0) {
    throw new Error("DASHBOARD_USERS must include at least one user");
  }
  cachedUsers = await Promise.all(entries.map(normalizeUser));
  return cachedUsers;
}

export function resetDashboardUsersCache(): void {
  cachedUsers = null;
}

export async function authenticateUser(
  username: string,
  password: string,
): Promise<DashboardUser | null> {
  const users = await loadDashboardUsers();
  const user = users.find((u) => u.username === username);
  if (!user) {
    return null;
  }
  const valid = await verifyPassword(password, user.passwordHash);
  return valid ? user : null;
}
