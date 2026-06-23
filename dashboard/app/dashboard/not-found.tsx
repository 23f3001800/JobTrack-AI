/**
 * Not Found page for dashboard routes.
 *
 * Shows when a user navigates to a dashboard URL that doesn't exist.
 * Provides a friendly message and link back to the main dashboard.
 */

import Link from "next/link";

export default function DashboardNotFound() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        textAlign: "center",
      }}
    >
      <div className="glass-card" style={{ padding: "var(--space-2xl)", maxWidth: 400 }}>
        <div style={{ fontSize: "4rem", marginBottom: "var(--space-md)" }}>
          🔍
        </div>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "var(--space-sm)" }}>
          Page Not Found
        </h2>
        <p
          style={{
            color: "var(--text-secondary)",
            marginBottom: "var(--space-lg)",
          }}
        >
          The page you&apos;re looking for doesn&apos;t exist.
        </p>
        <Link href="/dashboard" className="btn btn-primary">
          🏠 Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
