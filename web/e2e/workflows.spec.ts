import { expect, test } from "@playwright/test";

import { gotoFounderPage, waitForBff } from "./fixtures/page-ready";

const navTargets = [
  { link: "Dashboard", path: "/dashboard", title: "Dashboard", bffPath: "dashboard/summary" },
  { link: "Opportunities", path: "/opportunities", title: "Opportunities", bffPath: "dashboard/opportunities" },
  { link: "Pipeline", path: "/pipeline", title: "Pipeline", bffPath: "dashboard/pipeline" },
  { link: "Reports", path: "/reports", title: "Reports", bffPath: "dashboard/reports" },
  { link: "Approvals", path: "/approvals", title: "Approvals", bffPath: "approvals" },
  { link: "Budget", path: "/budget", title: "Budget", bffPath: "budget" },
  { link: "Agent Activity", path: "/agents", title: "Agent Activity", bffPath: "dashboard/summary" },
] as const;

test.describe("dashboard workflows", () => {
  test("sidebar navigation reaches each founder page", async ({ page }) => {
    await gotoFounderPage(page, "/dashboard", {
      title: "Dashboard",
      bffPath: "dashboard/summary",
    });

    for (const target of navTargets.slice(1)) {
      const responsePromise = page.waitForResponse(
        (response) =>
          response.url().includes(`/api/v1/${target.bffPath}`) &&
          response.request().method() === "GET" &&
          response.ok(),
      );
      await page.getByRole("link", { name: target.link }).click();
      await responsePromise;
      await expect(page).toHaveURL(new RegExp(`${target.path}$`));
      await expect(page.getByRole("heading", { level: 1, name: target.title })).toBeVisible();
    }
  });

  test("reports page shows library and selection empty state", async ({ page }) => {
    await gotoFounderPage(page, "/reports", {
      title: "Reports",
      bffPath: "dashboard/reports",
    });

    await expect(page.getByRole("heading", { name: "Report library" })).toBeVisible();
    const emptyLibrary = page.getByText("No reports");

    if ((await emptyLibrary.count()) > 0) {
      await expect(emptyLibrary.first()).toBeVisible();
      await expect(page.getByText("Select a report")).toBeVisible();
      return;
    }

    const reportTitleButton = page.locator("table tbody tr").getByRole("button").first();
    await expect(reportTitleButton).toBeVisible();
    const markdownPromise = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v1/reports/") &&
        response.url().includes("/markdown") &&
        response.ok(),
    );
    await reportTitleButton.click();
    await markdownPromise;
    await expect(page.locator("article.prose")).toBeVisible();
  });

  test("opportunities page lists ranking or empty state", async ({ page }) => {
    await gotoFounderPage(page, "/opportunities", {
      title: "Opportunities",
      bffPath: "dashboard/opportunities",
    });

    await expect(page.getByRole("combobox").first()).toBeVisible();
    await expect(page.locator("table")).toBeVisible();
  });

  test("approvals workflow: filter pending and open detail panel", async ({ page }) => {
    await gotoFounderPage(page, "/approvals", {
      title: "Approvals",
      bffPath: "approvals",
    });

    await expect(page.getByRole("heading", { name: "Requests" })).toBeVisible();

    const pendingFilter = page.getByRole("combobox").first();
    await pendingFilter.selectOption("pending");
    await waitForBff(page, "approvals");

    const empty = page.getByText("No approval requests match your filters.");
    const requestRow = page.locator("table tbody tr").first();

    if ((await empty.count()) > 0) {
      await expect(empty).toBeVisible();
      await expect(page.getByText("Select an approval request.")).toBeVisible();
      return;
    }

    await requestRow.getByRole("button").first().click();
    await expect(page.getByRole("heading", { name: "Detail" })).toBeVisible();
    await expect(page.getByText("Select an approval request.")).toHaveCount(0);
  });

  test("pipeline page shows run history and status", async ({ page }) => {
    await gotoFounderPage(page, "/pipeline", {
      title: "Pipeline",
      bffPath: "dashboard/pipeline",
    });

    await expect(page.getByRole("heading", { name: /Run history/ })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Status" })).toBeVisible();
  });
});
