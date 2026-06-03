import { NextResponse } from "next/server";

import { authenticateUser } from "@/lib/auth/users";
import { createSessionToken, sessionCookieOptions } from "@/lib/auth/session";

export async function POST(request: Request) {
  let body: { username?: string; password?: string };
  try {
    body = (await request.json()) as { username?: string; password?: string };
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  const username = body.username?.trim();
  const password = body.password;
  if (!username || !password) {
    return NextResponse.json({ detail: "Username and password are required" }, { status: 400 });
  }

  try {
    const user = await authenticateUser(username, password);
    if (!user) {
      return NextResponse.json({ detail: "Invalid credentials" }, { status: 401 });
    }

    const token = await createSessionToken({
      username: user.username,
      role: user.role,
    });
    const response = NextResponse.json({
      username: user.username,
      role: user.role,
    });
    const cookie = sessionCookieOptions();
    response.cookies.set(cookie.name, token, cookie);
    return response;
  } catch (err) {
    const message = err instanceof Error ? err.message : "Authentication unavailable";
    return NextResponse.json({ detail: message }, { status: 500 });
  }
}
