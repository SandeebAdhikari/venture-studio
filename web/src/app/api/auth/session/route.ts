import { NextResponse } from "next/server";

import { getSessionFromCookies } from "@/lib/auth/session";

export async function GET() {
  const session = await getSessionFromCookies();
  if (!session) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  return NextResponse.json(session);
}
