import { test } from "@playwright/test";

import { gotoFounderPage } from "./fixtures/page-ready";

const founderPages = [
  { path: "/dashboard", title: "Dashboard", bffPath: "dashboard/summary" },
  { path: "/opportunities", title: "Opportunities", bffPath: "dashboard/opportunities" },
  { path: "/pipeline", title: "Pipeline", bffPath: "dashboard/pipeline" },
  { path: "/reports", title: "Reports", bffPath: "dashboard/reports" },
  { path: "/approvals", title: "Approvals", bffPath: "approvals" },
  { path: "/budget", title: "Budget", bffPath: "budget" },
] as const;

test.describe("authenticated page loads", () => {
  for (const pageDef of founderPages) {
    test(`${pageDef.title} page loads with live API data`, async ({ page }) => {
      await gotoFounderPage(page, pageDef.path, {
        title: pageDef.title,
        bffPath: pageDef.bffPath,
      });
    });
  }
});
