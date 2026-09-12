import React from "react";
import { Navigate } from "react-router";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../types/auth";

interface RequireAuthProps {
  allowed: Role[];
  children: React.ReactElement;
}

export function RequireAuth({ allowed, children }: RequireAuthProps) {
  const { isReady, token, role } = useAuth();

  if (!isReady) {
    return null;
  }

  if (!token || !role || !allowed.includes(role)) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
