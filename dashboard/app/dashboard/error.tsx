"use client";

/**
 * Error Boundary — catches unhandled errors in dashboard pages.
 *
 * WHY an error boundary?
 * Without this, a JavaScript error in one page crashes the entire
 * dashboard with a white screen. The error boundary catches the
 * error and shows a friendly message with a retry button.
 *
 * Next.js App Router uses error.tsx files as React error boundaries.
 * This file catches errors for all /dashboard/* routes.
 */

import { useEffect } from "react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  // Log the error for debugging
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div
      className="animate-fade-in"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        textAlign: "center",
        padding: "var(--space-2xl)",
      }}
    >
      <div
        className="glass-card"
        style={{
          padding: "var(--space-2xl)",
          maxWidth: 500,
        }}
      >
        {/* Error icon */}
        <div style={{ fontSize: "3rem", marginBottom: "var(--space-md)" }}>
          ⚠️
        </div>

        <h2
          style={{
            fontSize: "1.25rem",
            fontWeight: 600,
            marginBottom: "var(--space-sm)",
          }}
        >
          Something went wrong
        </h2>

        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "0.875rem",
            marginBottom: "var(--space-lg)",
            lineHeight: 1.5,
          }}
        >
          {error.message || "An unexpected error occurred. Please try again."}
        </p>

        {/* Error digest for support tickets */}
        {error.digest && (
          <p
            style={{
              fontFamily: "monospace",
              fontSize: "0.75rem",
              color: "var(--text-tertiary)",
              marginBottom: "var(--space-lg)",
            }}
          >
            Error ID: {error.digest}
          </p>
        )}

        <div style={{ display: "flex", gap: "var(--space-md)", justifyContent: "center" }}>
          <button className="btn btn-primary" onClick={() => reset()}>
            🔄 Try Again
          </button>
          <a href="/dashboard" className="btn btn-ghost">
            🏠 Go Home
          </a>
        </div>
      </div>
    </div>
  );
}
