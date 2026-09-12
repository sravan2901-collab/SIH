import { Routes, Route, Navigate } from "react-router";
import { Login } from "./pages/Login";
import { Scan } from "./pages/Scan";
import { Dashboard } from "./pages/Dashboard";
import { RequireAuth } from "./routes/RequireAuth";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/scan"
        element={
          <RequireAuth allowed={["Inspector"]}>
            <Scan />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth allowed={["Reviewer", "Admin"]}>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
