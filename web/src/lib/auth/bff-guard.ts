import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { apiForbiddenDetail, canProxyApi } from "@/lib/auth/rbac";
import { getSessionFromRequest } from "@/lib/auth/session";
import type { SessionUser } from "@/lib/auth/types";

export type BffAuthResult =
  | { ok: true; session: SessionUser }
  | { ok: false; response: NextResponse };

export async function authorizeBffRequest(
  request: NextRequest,
  apiPath: string,
): Promise<BffAuthResult> {
  const session = await getSessionFromRequest(request);
  if (!session) {
    return {
      ok: false,
      response: NextResponse.json({ detail: "Authentication required" }, { status: 401 }),
    };
  }

  if (!canProxyApi(request.method, apiPath, session.role)) {
    return {
      ok: false,
      response: NextResponse.json(
        { detail: apiForbiddenDetail(session.role, request.method, apiPath) },
        { status: 403 },
      ),
    };
  }

  return { ok: true, session };
}
