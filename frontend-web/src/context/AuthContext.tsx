import React, { createContext, useContext, useEffect, useState } from "react";
import { apiFetch } from "../lib/apiClient";
import type { CurrentUser, Role } from "../types/auth";

interface AuthContextType {
  token: string | null;
  role: Role | null;
  userId: string | null;
  isReady: boolean;
  setSession: (token: string, role: Role, userId: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = "lmpc_token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(() => !localStorage.getItem(TOKEN_STORAGE_KEY));

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!storedToken) {
      return;
    }

    let isMounted = true;

    apiFetch<CurrentUser>("/auth/me", {}, storedToken)
      .then((user) => {
        if (isMounted) {
          setToken(storedToken);
          setRole(user.role);
          setUserId(user.user_id);
        }
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        if (isMounted) {
          setToken(null);
          setRole(null);
          setUserId(null);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsReady(true);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const setSession = (newToken: string, newRole: Role, newUserId: string) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    setToken(newToken);
    setRole(newRole);
    setUserId(newUserId);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setRole(null);
    setUserId(null);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        role,
        userId,
        isReady,
        setSession,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// oxlint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
