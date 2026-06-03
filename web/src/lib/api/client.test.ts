import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, buildQuery, clientApiFetch } from "./client";

describe("buildQuery", () => {
  it("omits empty values", () => {
    expect(buildQuery({ limit: 10, offset: undefined, force: false })).toBe("?limit=10&force=false");
  });

  it("returns empty string when no params", () => {
    expect(buildQuery({})).toBe("");
  });
});

describe("clientApiFetch", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls the BFF proxy path", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "ok" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await clientApiFetch<{ status: string }>("/dashboard/summary");

    expect(result).toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/dashboard/summary",
      expect.objectContaining({
        headers: expect.objectContaining({ Accept: "application/json" }),
      }),
    );
  });

  it("throws ApiError for failed responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () => "Unauthorized",
      }),
    );

    await expect(clientApiFetch("/dashboard/summary")).rejects.toEqual(
      expect.objectContaining<Partial<ApiError>>({
        name: "ApiError",
        status: 401,
        message: "Unauthorized",
      }),
    );
  });
});
