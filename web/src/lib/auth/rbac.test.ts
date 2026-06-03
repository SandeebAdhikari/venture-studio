import { describe, expect, it } from "vitest";

import { canAccessPage, canProxyApi, isProtectedPage } from "@/lib/auth/rbac";

describe("isProtectedPage", () => {
  it("marks founder dashboard routes as protected", () => {
    expect(isProtectedPage("/dashboard")).toBe(true);
    expect(isProtectedPage("/pipeline")).toBe(true);
    expect(isProtectedPage("/login")).toBe(false);
  });
});

describe("canAccessPage", () => {
  it("allows founder to access operational pages", () => {
    expect(canAccessPage("/pipeline", "founder")).toBe(true);
    expect(canAccessPage("/agents", "founder")).toBe(true);
  });

  it("allows admin operational pages", () => {
    expect(canAccessPage("/approvals", "admin")).toBe(true);
    expect(canAccessPage("/pipeline", "admin")).toBe(true);
  });

  it("restricts viewer to read-only pages", () => {
    expect(canAccessPage("/dashboard", "viewer")).toBe(true);
    expect(canAccessPage("/reports", "viewer")).toBe(true);
    expect(canAccessPage("/pipeline", "viewer")).toBe(false);
    expect(canAccessPage("/approvals", "viewer")).toBe(false);
    expect(canAccessPage("/agents", "viewer")).toBe(false);
  });
});

describe("canProxyApi", () => {
  it("allows viewer GET on dashboard paths", () => {
    expect(canProxyApi("GET", "dashboard/summary", "viewer")).toBe(true);
    expect(canProxyApi("GET", "budget", "viewer")).toBe(true);
  });

  it("denies viewer mutating requests", () => {
    expect(canProxyApi("POST", "approvals/abc/approve", "viewer")).toBe(false);
    expect(canProxyApi("PATCH", "opportunities/1", "viewer")).toBe(false);
  });

  it("allows admin approval mutations", () => {
    expect(canProxyApi("POST", "approvals/abc/approve", "admin")).toBe(true);
    expect(canProxyApi("GET", "approvals", "admin")).toBe(true);
  });

  it("blocks admin destructive platform routes", () => {
    expect(canProxyApi("DELETE", "sources/1", "admin")).toBe(false);
    expect(canProxyApi("POST", "rss-feeds", "admin")).toBe(false);
  });

  it("allows founder full API access", () => {
    expect(canProxyApi("DELETE", "sources/1", "founder")).toBe(true);
    expect(canProxyApi("POST", "scheduler/run/collect", "founder")).toBe(true);
  });

  it("denies viewer access to approvals reads", () => {
    expect(canProxyApi("GET", "approvals", "viewer")).toBe(false);
  });
});
