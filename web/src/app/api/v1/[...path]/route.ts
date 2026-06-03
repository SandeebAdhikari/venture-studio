/**
 * BFF proxy — forwards authenticated requests to the FastAPI backend.
 * Keeps API_KEY server-side while enabling client polling and mutations.
 */

import { NextRequest, NextResponse } from "next/server";

function getApiBaseUrl(): string {
  const url = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return url.replace(/\/$/, "");
}

async function proxyRequest(request: NextRequest, pathSegments: string[]) {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    return NextResponse.json({ detail: "API_KEY is not configured" }, { status: 500 });
  }

  const path = pathSegments.join("/");
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

  const response = await fetch(url, {
    method: request.method,
    headers,
    body: body || undefined,
    cache: "no-store",
  });

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
