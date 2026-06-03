import { expect, test } from "@playwright/test";

import { gotoFounderPage } from "./fixtures/page-ready";
import { seedE2eFixtures } from "./fixtures/seed";

test.beforeAll(() => {
  seedE2eFixtures();
});

test.describe("pipeline execution visibility", () => {
  test("run history shows completed E2E fixture run with status", async ({ page }) => {
    await gotoFounderPage(page, "/pipeline", {
      title: "Pipeline",
      bffPath: "dashboard/pipeline",
    });

    await expect(page.getByRole("heading", { name: /Run history/ })).toBeVisible();
    const statusCell = page.locator("table tbody tr").first().getByRole("cell").filter({
      hasText: /completed|partial|failed|running/i,
    });
    await expect(statusCell.first()).toBeVisible();

    const stageSection = page.getByText(/Stage runs|stages/i);
    if ((await stageSection.count()) > 0) {
      await expect(stageSection.first()).toBeVisible();
    }
  });
});
