"use client";

import { useEffect, useState } from "react";
import { getApplications, updateStatus, type Application } from "@/lib/api";

/**
 * Tracker Page — application list with status management.
 *
 * WHY a table view instead of a Kanban board?
 * Phase 4 focuses on foundation. The table gives immediate value:
 * - Sort/filter by status, company, quality
 * - Status dropdown for quick updates
 * - Expandable rows to view generated materials
 * Phase 7 will add a full Kanban drag-and-drop board.
 */

const STATUS_OPTIONS = [
  "saved",
  "applied",
  "screening",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
];

export default function TrackerPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    getApplications()
      .then((data) => setApps(data.applications))
      .catch(() => setApps([]))
      .finally(() => setLoading(false));
  }, []);

  /** Handle status change from dropdown */
  const handleStatusChange = async (
    appId: string | number,
    newStatus: string
  ) => {
    try {
      await updateStatus(String(appId), newStatus);
      // Update local state immediately for snappy UX
      setApps((prev) =>
        prev.map((a, i) =>
          (a.id || String(i)) === String(appId)
            ? { ...a, status: newStatus }
            : a
        )
      );
    } catch {
      // Silent fail — status will refresh on next load
    }
  };

  /** Toggle expanded row to show generated materials */
  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  // Filter applications by status
  const filtered =
    filter === "all" ? apps : apps.filter((a) => a.status === filter);

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <h1>📋 Application Tracker</h1>
        <p>
          {apps.length} application{apps.length !== 1 ? "s" : ""} tracked
        </p>
      </div>

      {/* Filter bar */}
      <div
        style={{
          display: "flex",
          gap: "var(--space-sm)",
          marginBottom: "var(--space-lg)",
          flexWrap: "wrap",
        }}
      >
        <button
          className={`btn ${filter === "all" ? "btn-primary" : "btn-ghost"}`}
          onClick={() => setFilter("all")}
          style={{ fontSize: "0.8125rem", padding: "0.375rem 0.75rem" }}
        >
          All ({apps.length})
        </button>
        {STATUS_OPTIONS.map((s) => {
          const count = apps.filter((a) => a.status === s).length;
          if (count === 0) return null;
          return (
            <button
              key={s}
              className={`btn ${filter === s ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setFilter(s)}
              style={{ fontSize: "0.8125rem", padding: "0.375rem 0.75rem" }}
            >
              {s} ({count})
            </button>
          );
        })}
      </div>

      {/* Applications table */}
      <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
        {loading ? (
          <div className="skeleton" style={{ height: 300 }} />
        ) : filtered.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "var(--space-2xl)",
              color: "var(--text-tertiary)",
            }}
          >
            <p style={{ fontSize: "2rem", marginBottom: "var(--space-sm)" }}>
              📭
            </p>
            <p>
              {filter === "all"
                ? "No applications yet"
                : `No ${filter} applications`}
            </p>
          </div>
        ) : (
          <table className="app-table">
            <thead>
              <tr>
                <th></th>
                <th>Company</th>
                <th>Position</th>
                <th>Status</th>
                <th>Quality</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((app, i) => {
                const appId = app.id || String(i);
                const isExpanded = expandedId === appId;

                return (
                  <>
                    {/* Main row */}
                    <tr
                      key={appId}
                      onClick={() => toggleExpand(appId)}
                      style={{ cursor: "pointer" }}
                    >
                      <td style={{ width: 30, fontSize: "0.75rem" }}>
                        {isExpanded ? "▼" : "▶"}
                      </td>
                      <td style={{ fontWeight: 500 }}>{app.company}</td>
                      <td>{app.job_title}</td>
                      <td>
                        {/* Status dropdown — click stops propagation to prevent row toggle */}
                        <select
                          className="input"
                          value={app.status || "applied"}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleStatusChange(appId, e.target.value);
                          }}
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            width: "auto",
                            padding: "0.25rem 0.5rem",
                            fontSize: "0.75rem",
                            background: "var(--bg-input)",
                          }}
                        >
                          {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        {app.quality_score ? (
                          <span
                            className="quality-score"
                            data-score={app.quality_score}
                          >
                            {app.quality_score}/5
                          </span>
                        ) : (
                          <span style={{ color: "var(--text-tertiary)" }}>
                            —
                          </span>
                        )}
                      </td>
                      <td
                        style={{
                          color: "var(--text-secondary)",
                          fontSize: "0.8125rem",
                        }}
                      >
                        {app.applied_at
                          ? new Date(app.applied_at).toLocaleDateString()
                          : "—"}
                      </td>
                    </tr>

                    {/* Expanded details row */}
                    {isExpanded && (
                      <tr key={`${appId}-detail`}>
                        <td colSpan={6} style={{ padding: "var(--space-lg)" }}>
                          <div
                            style={{
                              display: "grid",
                              gridTemplateColumns: "1fr 1fr",
                              gap: "var(--space-md)",
                            }}
                          >
                            {/* Cover letter */}
                            {app.cover_letter && (
                              <div>
                                <h4
                                  style={{
                                    fontSize: "0.8125rem",
                                    color: "var(--text-secondary)",
                                    marginBottom: "var(--space-xs)",
                                  }}
                                >
                                  ✉️ Cover Letter
                                </h4>
                                <pre
                                  style={{
                                    fontSize: "0.8125rem",
                                    whiteSpace: "pre-wrap",
                                    background: "var(--bg-input)",
                                    padding: "var(--space-md)",
                                    borderRadius: "var(--radius-md)",
                                    maxHeight: 300,
                                    overflow: "auto",
                                  }}
                                >
                                  {app.cover_letter}
                                </pre>
                              </div>
                            )}

                            {/* Tailored bullets */}
                            {app.tailored_bullets && (
                              <div>
                                <h4
                                  style={{
                                    fontSize: "0.8125rem",
                                    color: "var(--text-secondary)",
                                    marginBottom: "var(--space-xs)",
                                  }}
                                >
                                  📝 Tailored CV Bullets
                                </h4>
                                <pre
                                  style={{
                                    fontSize: "0.8125rem",
                                    whiteSpace: "pre-wrap",
                                    background: "var(--bg-input)",
                                    padding: "var(--space-md)",
                                    borderRadius: "var(--radius-md)",
                                    maxHeight: 300,
                                    overflow: "auto",
                                  }}
                                >
                                  {app.tailored_bullets}
                                </pre>
                              </div>
                            )}

                            {/* Role fit */}
                            {app.role_fit && (
                              <div>
                                <h4
                                  style={{
                                    fontSize: "0.8125rem",
                                    color: "var(--text-secondary)",
                                    marginBottom: "var(--space-xs)",
                                  }}
                                >
                                  🎯 Role Fit Analysis
                                </h4>
                                <pre
                                  style={{
                                    fontSize: "0.8125rem",
                                    whiteSpace: "pre-wrap",
                                    background: "var(--bg-input)",
                                    padding: "var(--space-md)",
                                    borderRadius: "var(--radius-md)",
                                    maxHeight: 300,
                                    overflow: "auto",
                                  }}
                                >
                                  {app.role_fit}
                                </pre>
                              </div>
                            )}

                            {/* DM */}
                            {app.outreach_dm && (
                              <div>
                                <h4
                                  style={{
                                    fontSize: "0.8125rem",
                                    color: "var(--text-secondary)",
                                    marginBottom: "var(--space-xs)",
                                  }}
                                >
                                  💬 LinkedIn DM
                                </h4>
                                <pre
                                  style={{
                                    fontSize: "0.8125rem",
                                    whiteSpace: "pre-wrap",
                                    background: "var(--bg-input)",
                                    padding: "var(--space-md)",
                                    borderRadius: "var(--radius-md)",
                                  }}
                                >
                                  {app.outreach_dm}
                                </pre>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
