import { expect, test } from "@playwright/test";

import { gotoFounderPage, waitForBff } from "./fixtures/page-ready";
import { seedE2eFixtures } from "./fixtures/seed";

test.describe.configure({ mode: "serial" });

test.beforeAll(() => {
  seedE2eFixtures();
});

test.describe("approval mutations", () => {
  test("venture report: draft visible before approval", async ({ page }) => {
    await gotoFounderPage(page, "/reports", {
      title: "Reports",
      bffPath: "dashboard/reports",
    });
    await expect(page.locator("table tbody").getByText("draft").first()).toBeVisible();
  });

  test("venture report: approve publishes report", async ({ page }) => {
    await gotoFounderPage(page, "/approvals", {
      title: "Approvals",
      bffPath: "approvals",
    });

    await page.getByRole("combobox").nth(0).selectOption("pending");
    await page.getByRole("combobox").nth(1).selectOption("venture_report");
    await waitForBff(page, "approvals");

    const row = page.locator("table tbody tr").first();
    await expect(row).toBeVisible();
    await row.getByRole("button").first().click();

    const approveResponse = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v1/approvals/") &&
        response.url().endsWith("/approve") &&
        response.request().method() === "POST" &&
        response.ok(),
    );
    await page.getByRole("button", { name: "Approve" }).click();
    await approveResponse;

    await page.getByRole("combobox").nth(0).selectOption("approved");
    await waitForBff(page, "approvals");
    await expect(page.getByText("approved").first()).toBeVisible();

    await gotoFounderPage(page, "/reports", {
      title: "Reports",
      bffPath: "dashboard/reports",
    });
    await expect(page.locator("table tbody").getByText("published").first()).toBeVisible();
  });

  test("executive ranking: reject pending request", async ({ page }) => {
    await gotoFounderPage(page, "/approvals", {
      title: "Approvals",
      bffPath: "approvals",
    });

    await page.getByRole("combobox").nth(0).selectOption("pending");
    await page.getByRole("combobox").nth(1).selectOption("executive_ranking");
    await waitForBff(page, "approvals");

    const row = page.locator("table tbody tr").first();
    await expect(row).toBeVisible();
    await row.getByRole("button").first().click();

    const rejectResponse = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v1/approvals/") &&
        response.url().endsWith("/reject") &&
        response.request().method() === "POST" &&
        response.ok(),
    );
    await page.getByRole("button", { name: "Reject" }).click();
    await rejectResponse;

    await page.getByRole("combobox").nth(0).selectOption("rejected");
    await waitForBff(page, "approvals");
    await expect(page.locator("table tbody").getByText("rejected").first()).toBeVisible();
  });

  test("venture report: request research requires comment and updates status", async ({ page }) => {
    await gotoFounderPage(page, "/approvals", {
      title: "Approvals",
      bffPath: "approvals",
    });

    await page.getByRole("combobox").nth(0).selectOption("pending");
    await page.getByRole("combobox").nth(1).selectOption("venture_report");
    await waitForBff(page, "approvals");

    const row = page.locator("table tbody tr").first();
    await expect(row).toBeVisible();
    await row.getByRole("button").first().click();

    await page.getByRole("button", { name: "Request research" }).click();
    await expect(page.locator("p.text-destructive")).toBeVisible();

    await page
      .getByPlaceholder("Optional comment (required for research request)")
      .fill("Need deeper competitor validation before publish.");

    const researchResponse = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v1/approvals/") &&
        response.url().endsWith("/research") &&
        response.request().method() === "POST" &&
        response.ok(),
    );
    await page.getByRole("button", { name: "Request research" }).click();
    await researchResponse;

    await page.getByRole("combobox").nth(0).selectOption("research_requested");
    await waitForBff(page, "approvals");
    await expect(page.locator("table tbody").getByText("research requested").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Approve" })).toHaveCount(0);
  });
});
