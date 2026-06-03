/** Server-side API client — credentials never exposed to the browser. */

function getApiBaseUrl(): string {
  const url = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return url.replace(/\/$/, "");
}

function getApiKey(): string {
  const key = process.env.API_KEY;
  if (!key) {
    throw new Error("API_KEY is not configured");
  }
  return key;
}

export async function serverApiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1${path}`, {
    ...init,
    headers: {
      "X-API-Key": getApiKey(),
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API error ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
