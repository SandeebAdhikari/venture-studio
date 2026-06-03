import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";
import type { NextRequest } from "next/server";

import { DEFAULT_SESSION_MAX_AGE_SECONDS, SESSION_COOKIE_NAME } from "@/lib/auth/constants";
import type { DashboardRole, SessionPayload, SessionUser } from "@/lib/auth/types";

function getAuthSecret(): Uint8Array {
  const secret = process.env.AUTH_SECRET;
  if (!secret || secret.length < 32) {
    throw new Error("AUTH_SECRET must be set and at least 32 characters");
  }
  return new TextEncoder().encode(secret);
}

function sessionMaxAgeSeconds(): number {
  const raw = process.env.SESSION_MAX_AGE_SECONDS;
  if (!raw) {
    return DEFAULT_SESSION_MAX_AGE_SECONDS;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_SESSION_MAX_AGE_SECONDS;
}

export async function createSessionToken(user: SessionUser): Promise<string> {
  const maxAge = sessionMaxAgeSeconds();
  return new SignJWT({ role: user.role })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(user.username)
    .setIssuedAt()
    .setExpirationTime(`${maxAge}s`)
    .sign(getAuthSecret());
}

export async function verifySessionToken(token: string): Promise<SessionUser | null> {
  try {
    const { payload } = await jwtVerify(token, getAuthSecret(), {
      algorithms: ["HS256"],
    });
    const role = payload.role as DashboardRole | undefined;
    const username = payload.sub;
    if (!username || !role || !["founder", "admin", "viewer"].includes(role)) {
      return null;
    }
    return { username, role };
  } catch {
    return null;
  }
}

export function sessionCookieOptions(maxAge = sessionMaxAgeSeconds()) {
  return {
    name: SESSION_COOKIE_NAME,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export async function getSessionFromRequest(request: NextRequest): Promise<SessionUser | null> {
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (!token) {
    return null;
  }
  return verifySessionToken(token);
}

export async function getSessionFromCookies(): Promise<SessionUser | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) {
    return null;
  }
  return verifySessionToken(token);
}

export type { SessionPayload };
