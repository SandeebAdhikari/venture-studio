import { expect, test } from "@playwright/test";

import { loginViaUi } from "./fixtures/auth";
import { expectPageHealthy, waitForBff } from "./fixtures/page-ready";

test.describe("viewer role", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaUi(page, "viewer");
  });

  test("viewer can load allowed pages", async ({ page }) => {
    await page.goto("/dashboard");
    await waitForBff(page, "dashboard/summary");
    await expectPageHealthy(page, "Dashboard");

    await page.goto("/budget");
    await waitForBff(page, "budget");
    await expectPageHealthy(page, "Budget");
  });

  test("viewer sidebar omits operational pages", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForResponse(
      (response) => response.url().includes("/api/auth/session") && response.ok(),
    );
    await waitForBff(page, "dashboard/summary");

    const sidebarNav = page.locator("aside nav");
    await expect(sidebarNav.getByRole("link", { name: "Pipeline" })).toHaveCount(0);
    await expect(sidebarNav.getByRole("link", { name: "Approvals" })).toHaveCount(0);
    await expect(sidebarNav.getByRole("link", { name: "Reports" })).toBeVisible();
  });

  test("viewer is redirected from pipeline", async ({ page }) => {
    await page.goto("/pipeline");
    await expect(page).toHaveURL(/\/dashboard$/);
  });
});
