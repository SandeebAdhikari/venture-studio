import type { Page } from "@playwright/test";

export type E2ERole = "founder" | "viewer" | "admin";

const DEFAULT_PASSWORD = "e2e-test-password";

function credsFor(role: E2ERole): { username: string; password: string } {
  switch (role) {
    case "founder":
      return {
        username: process.env.E2E_USERNAME ?? "founder",
        password: process.env.E2E_PASSWORD ?? DEFAULT_PASSWORD,
      };
    case "viewer":
      return {
        username: process.env.E2E_VIEWER_USERNAME ?? "viewer",
        password: process.env.E2E_VIEWER_PASSWORD ?? DEFAULT_PASSWORD,
      };
    case "admin":
      return {
        username: process.env.E2E_ADMIN_USERNAME ?? "admin",
        password: process.env.E2E_ADMIN_PASSWORD ?? DEFAULT_PASSWORD,
      };
  }
}

/** Sign in through the dashboard login form and wait for a protected route. */
export async function loginViaUi(page: Page, role: E2ERole = "founder"): Promise<void> {
  const { username, password } = credsFor(role);
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/(dashboard|opportunities|reports|budget)/, { timeout: 20_000 });
}
