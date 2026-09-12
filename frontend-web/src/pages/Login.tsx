import React, { useState } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext";
import { apiFetch, ApiError } from "../lib/apiClient";
import { ROLE_HOME, type LoginResponse } from "../types/auth";

export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const auth = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const res = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      auth.setSession(res.access_token, res.role, res.user_id);
      navigate(ROLE_HOME[res.role], { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Cannot reach the server. Please check your connection.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F6F8] flex flex-col items-center justify-center p-4 font-sans antialiased text-[#1A1F26]">
      <div className="w-full max-w-md bg-white border border-[#D8DEE4] rounded-md shadow-none overflow-hidden">
        {/* Muted gold accent top bar (3-4px) */}
        <div className="h-1 bg-[#B8862E]" />

        <div className="p-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-[#1F3B57] tracking-tight">
              LMPC Compliance System
            </h1>
            <p className="text-sm text-[#5B6472] mt-1">
              Legal Metrology (Packaged Commodities) Rules Enforcement
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-5 p-3 rounded bg-[#B3261E]/10 border border-[#B3261E]/20 text-sm text-[#B3261E]"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email-input"
                className="block text-sm font-medium text-[#1A1F26] mb-1 text-left"
              >
                Email address
              </label>
              <input
                id="email-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                placeholder="officer@lmpc.gov"
                className="w-full px-3 py-2 text-sm border border-[#D8DEE4] rounded bg-white text-[#1A1F26] placeholder-[#5B6472]/60 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57] focus-visible:border-transparent"
              />
            </div>

            <div>
              <label
                htmlFor="password-input"
                className="block text-sm font-medium text-[#1A1F26] mb-1 text-left"
              >
                Password
              </label>
              <input
                id="password-input"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="w-full px-3 py-2 text-sm border border-[#D8DEE4] rounded bg-white text-[#1A1F26] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57] focus-visible:border-transparent"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 px-4 bg-[#1F3B57] hover:bg-[#16293D] disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57] focus-visible:ring-offset-2"
              >
                {isSubmitting ? "Signing in…" : "Sign in"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
