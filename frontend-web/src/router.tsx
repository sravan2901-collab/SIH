import React from "react";
import { Routes, Route, Navigate } from "react-router";
import { useAuth } from "./context/AuthContext";
import { Login } from "./pages/Login";
import { Scan } from "./pages/Scan";
import { Dashboard } from "./pages/Dashboard";
import type { Role } from "./types/auth";

export function ProtectedRoute({
  allowedRoles,
  children,
}: {
  allowedRoles: Role[];
  children: React.ReactElement;
}) {
  const { isReady, token, role } = useAuth();
  if (!isReady) return null;
  if (!token || !role || !allowedRoles.includes(role)) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/scan"
        element={
          <ProtectedRoute allowedRoles={["Inspector"]}>
            <Scan />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute allowedRoles={["Reviewer", "Admin"]}>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
