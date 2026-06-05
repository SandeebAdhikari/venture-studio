/**
 * BFF proxy — verifies dashboard session + RBAC, then forwards to FastAPI.
 * Injects X-API-Key server-side only for authorized requests.
 */

import { NextRequest, NextResponse } from "next/server";

import { authorizeBffRequest } from "@/lib/auth/bff-guard";

function getApiBaseUrl(): string {
  const url = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return url.replace(/\/$/, "");
}

async function proxyRequest(request: NextRequest, pathSegments: string[]) {
  const path = pathSegments.join("/");
  const auth = await authorizeBffRequest(request, path);
  if (!auth.ok) {
    return auth.response;
  }

  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    return NextResponse.json({ detail: "API_KEY is not configured" }, { status: 500 });
  }
  const url = new URL(`${getApiBaseUrl()}/api/v1/${path}`);
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  const headers = new Headers();
  headers.set("X-API-Key", apiKey);
  headers.set("Accept", "application/json");

  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("Content-Type", contentType);
  }

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.text();

  let response: Response;
  try {
    response = await fetch(url, {
      method: request.method,
      headers,
      body: body || undefined,
      cache: "no-store",
    });
  } catch (error) {
    const cause = error instanceof Error ? error.cause : undefined;
    const code =
      cause && typeof cause === "object" && "code" in cause
        ? String((cause as { code?: string }).code)
        : undefined;
    const unreachable = code === "ECONNREFUSED" || code === "ENOTFOUND" || code === "EHOSTUNREACH";

    console.error("[BFF proxy] upstream fetch failed:", url.toString(), error);

    return NextResponse.json(
      {
        detail: unreachable
          ? `Backend API is not reachable at ${getApiBaseUrl()}. Start it with: cd api && uvicorn app.main:app --reload --port 8000 (or docker compose up api).`
          : "Backend API request failed.",
        code: code ?? "UPSTREAM_FETCH_FAILED",
        upstream: getApiBaseUrl(),
      },
      { status: 503 },
    );
  }

  const responseBody = await response.text();
  return new NextResponse(responseBody, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json",
    },
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}
