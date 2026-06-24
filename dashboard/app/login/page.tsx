"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, signup, getProfile } from "@/lib/api";

/**
 * Login Page — glass card with email/password form.
 *
 * WHY client component?
 * Login requires form state, error handling, and localStorage access
 * (for storing JWT tokens). These are all client-side concerns.
 *
 * Supports both login and signup modes via a toggle.
 */
export default function LoginPage() {
  const router = useRouter();
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (isSignup) {
        // Create account, then prompt to log in
        const result = await signup(email, password);
        setSuccess(result.message + " — you can now log in.");
        setIsSignup(false);
      } else {
        // Log in, then check onboarding status
        await login(email, password);
        try {
          const profile = await getProfile() as { onboarding_complete?: boolean };
          if (profile && !profile.onboarding_complete) {
            router.push("/onboarding");
          } else {
            router.push("/dashboard");
          }
        } catch {
          // If profile fetch fails, default to dashboard
          router.push("/dashboard");
        }
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Dev mode: skip login with API key.
   * WHY offer this? During local development without Supabase,
   * there's no auth service. The API key fallback lets developers
   * test the dashboard without configuring Supabase credentials.
   */
  const handleDevLogin = () => {
    const apiKey = prompt("Enter your API key (from .env):");
    if (apiKey) {
      localStorage.setItem("jt_access_token", apiKey);
      router.push("/dashboard");
    }
  };

  return (
    <div className="login-container">
      <div className="login-card glass-card animate-fade-in">
        {/* Logo */}
        <h1>
          🎯 <span style={{
            background: "var(--accent-gradient)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}>AutoApply AI</span>
        </h1>
        <p className="login-subtitle">
          {isSignup ? "Create your account" : "Sign in to your dashboard"}
        </p>

        {/* Error / Success messages */}
        {error && <div className="error-msg">{error}</div>}
        {success && <div className="success-msg">{success}</div>}

        {/* Login form */}
        <form className="login-form" onSubmit={handleSubmit}>
          <div>
            <label className="input-label" htmlFor="email">Email</label>
            <input
              id="email"
              className="input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div>
            <label className="input-label" htmlFor="password">Password</label>
            <input
              id="password"
              className="input"
              type="password"
              placeholder="Min. 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete={isSignup ? "new-password" : "current-password"}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? "Please wait..." : isSignup ? "Create Account" : "Sign In"}
          </button>
        </form>

        {/* Toggle login/signup */}
        <div className="login-footer">
          {isSignup ? (
            <p>
              Already have an account?{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); setIsSignup(false); }}>
                Sign in
              </a>
            </p>
          ) : (
            <p>
              Don&apos;t have an account?{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); setIsSignup(true); }}>
                Sign up
              </a>
            </p>
          )}

          {/* Dev mode shortcut */}
          <p style={{ marginTop: "var(--space-md)" }}>
            <a href="#" onClick={(e) => { e.preventDefault(); handleDevLogin(); }}
               style={{ fontSize: "0.75rem" }}>
              Dev mode: use API key →
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
