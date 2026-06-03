import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { authorizeBffRequest } from "@/lib/auth/bff-guard";
import { createSessionToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/constants";

const TEST_SECRET = "test-auth-secret-with-32-chars-minimum!!";

function requestWithSession(
  method: string,
  path: string,
  token: string | null,
): NextRequest {
  const url = `http://localhost/api/v1/${path}`;
  const headers = new Headers();
  if (token) {
    headers.set("cookie", `${SESSION_COOKIE_NAME}=${token}`);
  }
  return new NextRequest(url, { method, headers });
}

describe("authorizeBffRequest", () => {
  beforeEach(() => {
    vi.stubEnv("AUTH_SECRET", TEST_SECRET);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns 401 without session", async () => {
    const result = await authorizeBffRequest(
      requestWithSession("GET", "dashboard/summary", null),
      "dashboard/summary",
    );
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.response.status).toBe(401);
    }
  });

  it("allows authenticated founder", async () => {
    const token = await createSessionToken({ username: "founder", role: "founder" });
    const result = await authorizeBffRequest(
      requestWithSession("GET", "dashboard/summary", token),
      "dashboard/summary",
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.session.role).toBe("founder");
    }
  });

  it("returns 403 when viewer mutates", async () => {
    const token = await createSessionToken({ username: "viewer", role: "viewer" });
    const result = await authorizeBffRequest(
      requestWithSession("POST", "approvals/1/approve", token),
      "approvals/1/approve",
    );
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.response.status).toBe(403);
    }
  });
});
