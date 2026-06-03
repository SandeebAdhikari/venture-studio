export type DashboardRole = "founder" | "admin" | "viewer";

export interface DashboardUser {
  username: string;
  role: DashboardRole;
  passwordHash: string;
}

export interface SessionPayload {
  sub: string;
  role: DashboardRole;
  iat: number;
  exp: number;
}

export interface SessionUser {
  username: string;
  role: DashboardRole;
}
