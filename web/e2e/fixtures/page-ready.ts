import { expect, type Page } from "@playwright/test";

/** Wait for a successful BFF response before asserting page content. */
export async function waitForBff(
  page: Page,
  pathFragment: string,
  options?: { timeout?: number },
): Promise<void> {
  await page.waitForResponse(
    (response) =>
      response.url().includes(`/api/v1/${pathFragment}`) &&
      response.request().method() === "GET" &&
      response.ok(),
    { timeout: options?.timeout ?? 30_000 },
  );
}

/** Page loaded without the dashboard error retry banner. */
export async function expectPageHealthy(page: Page, title: string): Promise<void> {
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
}

export async function gotoFounderPage(
  page: Page,
  path: string,
  options: { title: string; bffPath: string },
): Promise<void> {
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().includes(`/api/v1/${options.bffPath}`) &&
      response.request().method() === "GET",
    { timeout: 30_000 },
  );
  await page.goto(path);
  const response = await responsePromise;
  expect(response.ok(), `BFF ${options.bffPath} should return 200`).toBeTruthy();
  await expectPageHealthy(page, options.title);
}
