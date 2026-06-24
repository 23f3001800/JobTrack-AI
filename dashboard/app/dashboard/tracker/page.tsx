"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getApplications, updateStatus, deleteApplication, updateNotes, type Application } from "@/lib/api";
import { useToast } from "@/components/Toast";

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
  "draft",
  "saved",
  "applied",
  "screening",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
];

export default function TrackerPage() {
  const router = useRouter();
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const { toast } = useToast();

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
      toast(`Status updated to ${newStatus}`, "success");
    } catch {
      toast("Failed to update status", "error");
    }
  };

  /** Toggle expanded row to show generated materials */
  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  // Filter applications by status
  const filtered =
    filter === "all" ? apps : apps.filter((a) => a.status === filter);

  /** Export applications to CSV file */
  const handleExportCSV = () => {
    if (apps.length === 0) return;

    const headers = [
      "Company",
      "Position",
      "Status",
      "Quality Score",
      "Applied Date",
    ];
    const rows = apps.map((a) => [
      `"${(a.company || "").replace(/"/g, '""')}"`,
      `"${(a.job_title || "").replace(/"/g, '""')}"`,
      a.status || "applied",
      a.quality_score ? String(a.quality_score) : "",
      a.applied_at
        ? new Date(a.applied_at).toLocaleDateString()
        : "",
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join(
      "\n"
    );
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `autoapply_export_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    toast(`Exported ${apps.length} applications`, "success");
  };

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>📋 Application Tracker</h1>
          <p>
            {apps.length} application{apps.length !== 1 ? "s" : ""} tracked
          </p>
        </div>
        {apps.length > 0 && (
          <button
            className="btn btn-ghost"
            onClick={handleExportCSV}
            style={{ fontSize: "0.8125rem", marginTop: "var(--space-xs)" }}
          >
            📥 Export CSV
          </button>
        )}
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
                // Find the original index in the full apps array for review link
                const originalIndex = apps.indexOf(app);
                const appId = app.id || String(originalIndex !== -1 ? originalIndex : i);
                const isExpanded = expandedId === appId;
                const isDraft = app.status === "draft";

                return (
                  <>
                    {/* Main row */}
                    <tr
                      key={appId}
                      onClick={() => !isDraft && toggleExpand(appId)}
                      style={{ cursor: isDraft ? "default" : "pointer" }}
                    >
                      <td style={{ width: 30, fontSize: "0.75rem" }}>
                        {isDraft ? (
                          "📝"
                        ) : (
                          isExpanded ? "▼" : "▶"
                        )}
                      </td>
                      <td style={{ fontWeight: 500 }}>{app.company}</td>
                      <td>{app.job_title}</td>
                      <td>
                        {isDraft ? (
                          <button
                            className="btn btn-primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/dashboard/review/${appId}`);
                            }}
                            style={{
                              fontSize: "0.75rem",
                              padding: "0.25rem 0.75rem",
                            }}
                          >
                            📋 Review
                          </button>
                        ) : (
                          /* Status dropdown — click stops propagation to prevent row toggle */
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
                        )}
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

                    {/* Expanded details row — full-width Application Detail View */}
                    {isExpanded && (
                      <tr key={`${appId}-detail`}>
                        <td colSpan={6} style={{ padding: 0 }}>
                          <div
                            style={{
                              padding: "var(--space-lg)",
                              display: "flex",
                              flexDirection: "column",
                              gap: "var(--space-md)",
                            }}
                          >
                            {/* ── Detail Header ── */}
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                flexWrap: "wrap",
                                gap: "var(--space-md)",
                                paddingBottom: "var(--space-md)",
                                borderBottom: "1px solid rgba(255,255,255,0.06)",
                              }}
                            >
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <h3
                                  style={{
                                    fontSize: "1.125rem",
                                    fontWeight: 600,
                                    marginBottom: "var(--space-xs)",
                                  }}
                                >
                                  {app.company} — {app.job_title}
                                </h3>
                                <span
                                  style={{
                                    fontSize: "0.8125rem",
                                    color: "var(--text-secondary)",
                                  }}
                                >
                                  {app.applied_at
                                    ? `Applied ${new Date(app.applied_at).toLocaleDateString()}`
                                    : "Date not recorded"}
                                </span>
                              </div>
                              <span
                                className="badge badge-applied"
                                style={{ textTransform: "capitalize" }}
                              >
                                {app.status || "applied"}
                              </span>
                              {app.quality_score != null && (
                                <span
                                  style={{
                                    display: "inline-block",
                                    padding: "0.25rem 0.625rem",
                                    borderRadius: "var(--radius-md)",
                                    fontSize: "0.8125rem",
                                    fontWeight: 600,
                                    background:
                                      app.quality_score >= 4
                                        ? "rgba(52,211,153,0.15)"
                                        : app.quality_score === 3
                                        ? "rgba(251,191,36,0.15)"
                                        : "rgba(248,113,113,0.15)",
                                    color:
                                      app.quality_score >= 4
                                        ? "var(--quality-high, #34d399)"
                                        : app.quality_score === 3
                                        ? "var(--quality-mid, #fbbf24)"
                                        : "var(--quality-low, #f87171)",
                                  }}
                                >
                                  ⭐ {app.quality_score}/5
                                </span>
                              )}
                            </div>

                            {/* ── Job Analysis ── */}
                            {app.job_analysis && (
                              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                                <h4
                                  style={{
                                    fontSize: "0.875rem",
                                    fontWeight: 600,
                                    marginBottom: "var(--space-sm)",
                                  }}
                                >
                                  📋 Job Analysis
                                </h4>
                                <pre
                                  style={{
                                    fontSize: "0.8125rem",
                                    whiteSpace: "pre-wrap",
                                    background: "var(--bg-input)",
                                    padding: "var(--space-md)",
                                    borderRadius: "var(--radius-md)",
                                    maxHeight: 400,
                                    overflow: "auto",
                                    color: "var(--text-secondary)",
                                  }}
                                >
                                  {app.job_analysis}
                                </pre>
                              </div>
                            )}

                            {/* ── Company Profile ── */}
                            {app.company_profile && (
                              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                                <h4
                                  style={{
                                    fontSize: "0.875rem",
                                    fontWeight: 600,
                                    marginBottom: "var(--space-sm)",
                                  }}
                                >
                                  🏢 Company Profile
                                </h4>
                                <pre
                                  style={{
                                    fontSize: "0.8125rem",
                                    whiteSpace: "pre-wrap",
                                    background: "var(--bg-input)",
                                    padding: "var(--space-md)",
                                    borderRadius: "var(--radius-md)",
                                    maxHeight: 400,
                                    overflow: "auto",
                                    color: "var(--text-secondary)",
                                  }}
                                >
                                  {app.company_profile}
                                </pre>
                              </div>
                            )}

                            {/* ── Role Fit ── */}
                            {app.role_fit && (
                              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                                <h4
                                  style={{
                                    fontSize: "0.875rem",
                                    fontWeight: 600,
                                    marginBottom: "var(--space-sm)",
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
                                    maxHeight: 400,
                                    overflow: "auto",
                                    color: "var(--text-secondary)",
                                  }}
                                >
                                  {app.role_fit}
                                </pre>
                              </div>
                            )}

                            {/* ── Cover Letter ── */}
                            {app.cover_letter && (
                              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                                <h4
                                  style={{
                                    fontSize: "0.875rem",
                                    fontWeight: 600,
                                    marginBottom: "var(--space-sm)",
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
                                    maxHeight: 400,
                                    overflow: "auto",
                                    color: "var(--text-secondary)",
                                  }}
                                >
                                  {app.cover_letter}
                                </pre>
                              </div>
                            )}

                            {/* ── Tailored CV Bullets ── */}
                            {app.tailored_bullets && (
                              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                                <h4
                                  style={{
                                    fontSize: "0.875rem",
                                    fontWeight: 600,
                                    marginBottom: "var(--space-sm)",
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
                                    maxHeight: 400,
                                    overflow: "auto",
                                    color: "var(--text-secondary)",
                                  }}
                                >
                                  {app.tailored_bullets}
                                </pre>
                              </div>
                            )}

                            {/* ── LinkedIn DM ── */}
                            {app.outreach_dm && (
                              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                                <h4
                                  style={{
                                    fontSize: "0.875rem",
                                    fontWeight: 600,
                                    marginBottom: "var(--space-sm)",
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
                                    maxHeight: 300,
                                    overflow: "auto",
                                    color: "var(--text-secondary)",
                                  }}
                                >
                                  {app.outreach_dm}
                                </pre>
                              </div>
                            )}

                            {/* ── Notes ── */}
                            <div>
                              <h4
                                style={{
                                  fontSize: "0.875rem",
                                  fontWeight: 600,
                                  marginBottom: "var(--space-sm)",
                                }}
                              >
                                🗒️ Notes
                              </h4>
                              <textarea
                                className="input"
                                placeholder="Add notes... (recruiter name, follow-up date, etc.)"
                                defaultValue={app.notes || ""}
                                rows={3}
                                style={{
                                  width: "100%",
                                  resize: "vertical",
                                  fontSize: "0.8125rem",
                                }}
                                onClick={(e) => e.stopPropagation()}
                                onBlur={async (e) => {
                                  const newNotes = e.target.value;
                                  if (newNotes !== (app.notes || "")) {
                                    try {
                                      await updateNotes(appId, newNotes);
                                      setApps((prev) =>
                                        prev.map((a, idx) =>
                                          (a.id || String(idx)) === appId
                                            ? { ...a, notes: newNotes }
                                            : a
                                        )
                                      );
                                      toast("Notes saved", "success");
                                    } catch {
                                      toast("Failed to save notes", "error");
                                    }
                                  }
                                }}
                              />
                            </div>

                            {/* ── Delete ── */}
                            <div style={{ textAlign: "right" }}>
                              <button
                                className="btn btn-ghost"
                                style={{
                                  fontSize: "0.75rem",
                                  color: "var(--error)",
                                  padding: "0.25rem 0.75rem",
                                }}
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  if (!confirm(`Delete application for ${app.company}?`)) return;
                                  try {
                                    await deleteApplication(appId);
                                    setApps((prev) =>
                                      prev.filter((a, idx) =>
                                        (a.id || String(idx)) !== appId
                                      )
                                    );
                                    setExpandedId(null);
                                    toast(`Deleted ${app.company}`, "success");
                                  } catch {
                                    toast("Failed to delete", "error");
                                  }
                                }}
                              >
                                🗑️ Delete Application
                              </button>
                            </div>
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
