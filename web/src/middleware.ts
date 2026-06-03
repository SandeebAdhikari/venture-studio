import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { canAccessPage, isProtectedPage } from "@/lib/auth/rbac";
import { getSessionFromRequest } from "@/lib/auth/session";

const AUTH_API_PREFIX = "/api/auth";
const BFF_API_PREFIX = "/api/v1";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith(AUTH_API_PREFIX)) {
    return NextResponse.next();
  }

  const session = await getSessionFromRequest(request);
  const isLoginPage = pathname === "/login";

  if (isLoginPage) {
    if (session) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return NextResponse.next();
  }

  const needsAuth =
    isProtectedPage(pathname) || pathname.startsWith(BFF_API_PREFIX);

  if (!needsAuth) {
    return NextResponse.next();
  }

  if (!session) {
    if (pathname.startsWith(BFF_API_PREFIX)) {
      return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
    }
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (isProtectedPage(pathname) && !canAccessPage(pathname, session.role)) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/dashboard/:path*",
    "/pipeline/:path*",
    "/approvals/:path*",
    "/reports/:path*",
    "/budget/:path*",
    "/agents/:path*",
    "/opportunities/:path*",
    "/api/v1/:path*",
  ],
};
