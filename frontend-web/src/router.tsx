import React from "react";
import { Routes, Route, Navigate } from "react-router";
import { useAuth } from "./context/AuthContext";
import { Login } from "./pages/Login";
import { ProductSelect } from "./pages/ProductSelect";
import { ScanUpload } from "./pages/ScanUpload";
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
        path="/products"
        element={
          <ProtectedRoute allowedRoles={["Inspector"]}>
            <ProductSelect />
          </ProtectedRoute>
        }
      />
      <Route
        path="/scan"
        element={
          <ProtectedRoute allowedRoles={["Inspector"]}>
            <ScanUpload />
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
