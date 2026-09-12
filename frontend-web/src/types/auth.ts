export type Role = "Inspector" | "Reviewer" | "Admin";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: Role;
  user_id: string;
}

export interface CurrentUser {
  user_id: string;
  name: string;
  email: string;
  role: Role;
  region: string | null;
}

export const ROLE_HOME: Record<Role, string> = {
  Inspector: "/scan",
  Reviewer: "/dashboard",
  Admin: "/dashboard",
};
