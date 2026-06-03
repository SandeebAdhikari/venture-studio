import { describe, expect, it } from "vitest";

import { cn, formatDate, formatDuration, formatPercent, formatUsd } from "./utils";

describe("cn", () => {
  it("merges tailwind classes", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });
});

describe("formatUsd", () => {
  it("formats currency values", () => {
    expect(formatUsd(12.5)).toBe("$12.50");
  });
});

describe("formatPercent", () => {
  it("formats percentage values", () => {
    expect(formatPercent(42.456)).toBe("42.5%");
  });
});

describe("formatDate", () => {
  it("returns em dash for empty values", () => {
    expect(formatDate(null)).toBe("—");
  });

  it("formats ISO timestamps", () => {
    expect(formatDate("2026-01-15T12:00:00.000Z")).toContain("2026");
  });
});

describe("formatDuration", () => {
  it("formats sub-second durations", () => {
    expect(formatDuration(250)).toBe("250ms");
  });

  it("formats minute durations", () => {
    expect(formatDuration(125_000)).toBe("2m 5s");
  });
});
