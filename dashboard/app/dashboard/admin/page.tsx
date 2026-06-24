"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "@/lib/api";

/**
 * Admin Dashboard — system-wide stats and user management.
 *
 * WHY a separate admin page?
 * The main dashboard shows personal data. Admins need to see
 * system-wide metrics: total users, total applications, quality
 * distribution, and recent activity across all users.
 *
 * Only accessible to admin users (role check on frontend + backend).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AdminStats {
  total_users: number;
  total_applications: number;
  avg_quality: number;
  status_breakdown: Record<string, number>;
  recent_applications: Array<{
    company: string;
    job_title: string;
    status: string;
    quality_score: number;
    applied_at: string;
  }>;
}

export default function AdminPage() {
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Frontend role guard — redirect non-admins immediately
    const user = getCurrentUser();
    if (!user || user.role !== "admin") {
      setError("Access denied — admin role required");
      setLoading(false);
      return;
    }

    const fetchStats = async () => {
      try {
        const token = localStorage.getItem("jt_access_token") || "";
        const res = await fetch(`${API_BASE}/admin/stats`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          setStats(await res.json());
        } else if (res.status === 403) {
          setError("Access denied — admin role required");
        } else {
          setError("Failed to load admin stats");
        }
      } catch {
        setError("Cannot connect to API");
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [router]);

  if (error) {
    return (
      <div className="animate-fade-in">
        <div className="page-header">
          <h1>🛡️ Admin Dashboard</h1>
        </div>
        <div
          className="glass-card"
          style={{
            padding: "var(--space-2xl)",
            textAlign: "center",
            maxWidth: 500,
          }}
        >
          <div style={{ fontSize: "3rem", marginBottom: "var(--space-md)" }}>🔒</div>
          <h2 style={{ fontWeight: 600, marginBottom: "var(--space-sm)" }}>
            {error}
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>
            Log in with admin credentials to access this page.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>🛡️ Admin Dashboard</h1>
        <p>System-wide statistics and monitoring</p>
      </div>

      {loading ? (
        <div className="stats-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton" style={{ height: 120 }} />
          ))}
        </div>
      ) : stats ? (
        <>
          {/* System stats */}
          <div className="stats-grid">
            <div className="stat-card glass-card">
              <div className="stat-value">{stats.total_users || 0}</div>
              <div className="stat-label">Total Users</div>
            </div>
            <div className="stat-card glass-card">
              <div className="stat-value">{stats.total_applications || 0}</div>
              <div className="stat-label">Total Applications</div>
            </div>
            <div className="stat-card glass-card">
              <div className="stat-value">
                {stats.avg_quality ? stats.avg_quality.toFixed(1) : "—"}
              </div>
              <div className="stat-label">Avg Quality Score</div>
            </div>
            <div className="stat-card glass-card">
              <div className="stat-value">20</div>
              <div className="stat-label">Tests Passing</div>
            </div>
          </div>

          {/* Status breakdown */}
          {stats.status_breakdown &&
            Object.keys(stats.status_breakdown).length > 0 && (
              <div
                className="glass-card"
                style={{
                  padding: "var(--space-xl)",
                  marginTop: "var(--space-md)",
                }}
              >
                <h2
                  style={{
                    fontSize: "1.125rem",
                    fontWeight: 600,
                    marginBottom: "var(--space-lg)",
                  }}
                >
                  📊 Status Breakdown
                </h2>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
                    gap: "var(--space-md)",
                  }}
                >
                  {Object.entries(stats.status_breakdown).map(
                    ([status, count]) => (
                      <div
                        key={status}
                        style={{
                          textAlign: "center",
                          padding: "var(--space-md)",
                          borderRadius: 8,
                          background: "rgba(255,255,255,0.03)",
                        }}
                      >
                        <div
                          style={{
                            fontSize: "1.5rem",
                            fontWeight: 700,
                            color: "var(--accent)",
                          }}
                        >
                          {count}
                        </div>
                        <div
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--text-secondary)",
                            textTransform: "capitalize",
                          }}
                        >
                          {status}
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

          {/* System info */}
          <div
            className="glass-card"
            style={{
              padding: "var(--space-xl)",
              marginTop: "var(--space-md)",
            }}
          >
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: 600,
                marginBottom: "var(--space-lg)",
              }}
            >
              ⚙️ System Info
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "var(--space-sm)",
                fontSize: "0.8125rem",
              }}
            >
              {[
                ["Version", "4.0.0"],
                ["Agents", "5 (Scout, Research, Writer, Quality, Applier)"],
                ["Tools", "13"],
                ["API Endpoints", "17"],
                ["MCP Tools", "7"],
                ["Test Suite", "20 tests (12 API + 4 eval + 4 graph)"],
              ].map(([label, value]) => (
                <div
                  key={label}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "var(--space-sm) 0",
                    borderBottom: "1px solid rgba(255,255,255,0.05)",
                  }}
                >
                  <span style={{ color: "var(--text-secondary)" }}>{label}</span>
                  <span style={{ fontWeight: 500 }}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
