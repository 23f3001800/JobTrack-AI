"use client";

import { useEffect, useState } from "react";
import { getApplications, type Application } from "@/lib/api";

/**
 * Dashboard Home — overview with stats cards and recent applications.
 *
 * WHY compute stats client-side instead of using /admin/stats?
 * /admin/stats requires admin auth. Regular JWT users don't have
 * admin access. Computing stats from their own /tracker data means
 * every user sees their personal dashboard without extra permissions.
 */
export default function DashboardPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getApplications()
      .then((data) => setApps(data.applications))
      .catch(() => setApps([]))
      .finally(() => setLoading(false));
  }, []);

  // Compute stats from the user's own applications
  const totalApps = apps.length;
  const avgQuality =
    apps.filter((a) => a.quality_score && a.quality_score > 0).length > 0
      ? (
          apps
            .filter((a) => a.quality_score && a.quality_score > 0)
            .reduce((sum, a) => sum + (a.quality_score || 0), 0) /
          apps.filter((a) => a.quality_score && a.quality_score > 0).length
        ).toFixed(1)
      : "—";
  const statusCounts = apps.reduce(
    (acc, a) => {
      const s = a.status || "applied";
      acc[s] = (acc[s] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Your job application overview</p>
      </div>

      {/* Stats cards */}
      {loading ? (
        <div className="stats-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton" style={{ height: 120 }} />
          ))}
        </div>
      ) : (
        <div className="stats-grid">
          <div className="stat-card glass-card">
            <div className="stat-value">{totalApps}</div>
            <div className="stat-label">Total Applications</div>
          </div>
          <div className="stat-card glass-card">
            <div className="stat-value">{avgQuality}</div>
            <div className="stat-label">Avg Quality Score</div>
          </div>
          <div className="stat-card glass-card">
            <div className="stat-value">{statusCounts["interview"] || 0}</div>
            <div className="stat-label">Interviews</div>
          </div>
          <div className="stat-card glass-card">
            <div className="stat-value">{statusCounts["offer"] || 0}</div>
            <div className="stat-label">Offers</div>
          </div>
        </div>
      )}

      {/* Recent applications table */}
      <div className="glass-card" style={{ padding: "var(--space-lg)", marginTop: "var(--space-md)" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "var(--space-md)" }}>
          Recent Applications
        </h2>

        {loading ? (
          <div className="skeleton" style={{ height: 200 }} />
        ) : apps.length === 0 ? (
          <div style={{ textAlign: "center", padding: "var(--space-2xl)", color: "var(--text-tertiary)" }}>
            <p style={{ fontSize: "2rem", marginBottom: "var(--space-sm)" }}>🚀</p>
            <p>No applications yet. Start by running the agent on a job URL!</p>
          </div>
        ) : (
          <table className="app-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Position</th>
                <th>Status</th>
                <th>Quality</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {apps.slice(0, 10).map((app, i) => (
                <tr key={app.id || i}>
                  <td style={{ fontWeight: 500 }}>{app.company}</td>
                  <td>{app.job_title}</td>
                  <td>
                    <span className={`badge badge-${app.status || "applied"}`}>
                      {app.status || "applied"}
                    </span>
                  </td>
                  <td>
                    {app.quality_score ? (
                      <span
                        className="quality-score"
                        data-score={app.quality_score}
                      >
                        {"★".repeat(app.quality_score)}
                        {"☆".repeat(5 - app.quality_score)}
                      </span>
                    ) : (
                      <span style={{ color: "var(--text-tertiary)" }}>—</span>
                    )}
                  </td>
                  <td style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
                    {app.applied_at
                      ? new Date(app.applied_at).toLocaleDateString()
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
