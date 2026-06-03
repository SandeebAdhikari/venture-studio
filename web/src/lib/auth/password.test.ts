import { describe, expect, it } from "vitest";

import { hashPassword, verifyPassword } from "@/lib/auth/password";

describe("password hashing", () => {
  it("hashes and verifies passwords", async () => {
    const hash = await hashPassword("test-password");
    expect(await verifyPassword("test-password", hash)).toBe(true);
    expect(await verifyPassword("wrong", hash)).toBe(false);
  });
});
