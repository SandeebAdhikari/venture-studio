import { mkdirSync } from "node:fs";
import { join } from "node:path";

import { chromium, type FullConfig } from "@playwright/test";

import { loginViaUi } from "./fixtures/auth";

const authFile = join(process.cwd(), "e2e", ".auth", "founder.json");

async function globalSetup(_config: FullConfig): Promise<void> {
  const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
  mkdirSync(join(process.cwd(), "e2e", ".auth"), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();

  await loginViaUi(page, "founder");
  await context.storageState({ path: authFile });
  await browser.close();
}

export default globalSetup;
