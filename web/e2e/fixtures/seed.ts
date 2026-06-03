import { execSync } from "node:child_process";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");

/** Run API seed script so approval / pipeline E2E have deterministic data. */
export function seedE2eFixtures(): void {
  const apiKey = process.env.E2E_API_KEY ?? process.env.API_KEY ?? "ci-github-actions-api-key";
  execSync("python scripts/seed_e2e_fixtures.py", {
    cwd: path.join(repoRoot, "api"),
    env: {
      ...process.env,
      PYTHONPATH: ".",
      REQUIRE_FOUNDER_APPROVAL: "true",
      API_KEY: apiKey,
      POSTGRES_HOST: process.env.POSTGRES_HOST ?? "localhost",
      POSTGRES_PORT: process.env.POSTGRES_PORT ?? "5432",
      POSTGRES_USER: process.env.POSTGRES_USER ?? "avs",
      POSTGRES_PASSWORD: process.env.POSTGRES_PASSWORD ?? "avs",
      POSTGRES_DB: process.env.POSTGRES_DB ?? "ai_venture_studio",
      REDIS_HOST: process.env.REDIS_HOST ?? "localhost",
      REDIS_PORT: process.env.REDIS_PORT ?? "6379",
    },
    stdio: "inherit",
  });
}
