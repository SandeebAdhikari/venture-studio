import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createSessionToken, verifySessionToken } from "@/lib/auth/session";

const TEST_SECRET = "test-auth-secret-with-32-chars-minimum!!";

describe("session tokens", () => {
  beforeEach(() => {
    vi.stubEnv("AUTH_SECRET", TEST_SECRET);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("creates and verifies a session", async () => {
    const token = await createSessionToken({ username: "founder", role: "founder" });
    const session = await verifySessionToken(token);
    expect(session).toEqual({ username: "founder", role: "founder" });
  });

  it("rejects tampered tokens", async () => {
    const token = await createSessionToken({ username: "admin", role: "admin" });
    const session = await verifySessionToken(`${token}x`);
    expect(session).toBeNull();
  });

  it("fails without AUTH_SECRET", async () => {
    vi.stubEnv("AUTH_SECRET", "");
    await expect(createSessionToken({ username: "x", role: "viewer" })).rejects.toThrow(
      /AUTH_SECRET/,
    );
  });
});
