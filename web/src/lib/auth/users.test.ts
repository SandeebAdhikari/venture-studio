import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authenticateUser, loadDashboardUsers, resetDashboardUsersCache } from "@/lib/auth/users";

const USERS_JSON = JSON.stringify([
  { username: "founder", password: "secret", role: "founder" },
  { username: "viewer", password: "view-only", role: "viewer" },
]);

describe("dashboard users", () => {
  beforeEach(() => {
    resetDashboardUsersCache();
    vi.stubEnv("DASHBOARD_USERS", USERS_JSON);
  });

  afterEach(() => {
    resetDashboardUsersCache();
    vi.unstubAllEnvs();
  });

  it("loads users from env", async () => {
    const users = await loadDashboardUsers();
    expect(users).toHaveLength(2);
    expect(users[0].passwordHash).toMatch(/^scrypt:/);
  });

  it("authenticates valid credentials", async () => {
    const user = await authenticateUser("founder", "secret");
    expect(user?.role).toBe("founder");
  });

  it("rejects invalid credentials", async () => {
    const user = await authenticateUser("founder", "wrong");
    expect(user).toBeNull();
  });
});
