"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getApplications,
  updateStatus,
  updateApplicationFields,
  deleteApplication,
  type Application,
} from "@/lib/api";
import { useToast } from "@/components/Toast";

/**
 * Review Page — human-in-the-loop approval workflow.
 *
 * WHY a dedicated review page instead of inline editing in the tracker?
 * 1. Full-screen editing experience for long-form content (cover letters, etc.)
 * 2. Clear draft → applied status transition with a single submit action
 * 3. Separates "review & edit" from "track & manage" concerns
 *
 * The page loads an application by its index in the tracker list,
 * lets the user edit AI-generated materials, then submits the final version.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const appId = params.id as string;

  // ── Application data ──
  const [app, setApp] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ── Editable fields ──
  const [coverLetter, setCoverLetter] = useState("");
  const [tailoredBullets, setTailoredBullets] = useState("");
  const [outreachDm, setOutreachDm] = useState("");

  // ── Collapsible sections ──
  const [showJobAnalysis, setShowJobAnalysis] = useState(false);
  const [showCompanyResearch, setShowCompanyResearch] = useState(false);
  const [showRoleFit, setShowRoleFit] = useState(false);

  // ── Action state ──
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // ── Fetch application on mount ──
  const fetchApp = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getApplications();
      const apps = data.applications || [];

      // Support both UUID-based lookup (Supabase) and index-based (JsonDB)
      let application = apps.find((a: Application) => String(a.id) === appId);
      if (!application) {
        // Fallback: try as array index (for JsonDB or legacy URLs)
        const index = parseInt(appId, 10);
        if (!isNaN(index) && index >= 0 && index < apps.length) {
          application = apps[index];
        }
      }
      if (!application) {
        setError("Application not found");
        return;
      }
      setApp(application);
      setCoverLetter(application.cover_letter || "");
      setTailoredBullets(application.tailored_bullets || "");
      setOutreachDm(application.outreach_dm || "");
    } catch {
      setError("Failed to load application");
    } finally {
      setLoading(false);
    }
  }, [appId]);

  useEffect(() => {
    fetchApp();
  }, [fetchApp]);

  // ── Quality score color coding ──
  const getScoreColor = (score: number) => {
    if (score >= 4) return { bg: "rgba(52,211,153,0.15)", color: "#34d399" };
    if (score === 3) return { bg: "rgba(251,191,36,0.15)", color: "#fbbf24" };
    return { bg: "rgba(248,113,113,0.15)", color: "#f87171" };
  };

  // ── Submit: save edits → update status to applied ──
  const handleSubmit = async () => {
    if (!app) return;
    setSubmitting(true);

    try {
      // 1. Save any field edits
      const fields: Record<string, string> = {};
      if (coverLetter !== (app.cover_letter || "")) fields.cover_letter = coverLetter;
      if (tailoredBullets !== (app.tailored_bullets || "")) fields.tailored_bullets = tailoredBullets;
      if (outreachDm !== (app.outreach_dm || "")) fields.outreach_dm = outreachDm;

      // Use the actual DB id (UUID for Supabase, or index-based for JSON)
      const dbId = app.id || appId;

      if (Object.keys(fields).length > 0) {
        await updateApplicationFields(String(dbId), fields);
      }

      // 2. Update status to applied
      await updateStatus(String(dbId), "applied");
      toast("Application submitted successfully!", "success");
      router.push("/dashboard/tracker");
    } catch {
      toast("Failed to submit application", "error");
    } finally {
      setSubmitting(false);
    }
  };

  // ── Discard: delete application ──
  const handleDiscard = async () => {
    if (!confirm("Discard this draft? This cannot be undone.")) return;
    setDeleting(true);

    try {
      // Use actual DB id, not URL param index
      const dbId = app?.id || appId;
      await deleteApplication(String(dbId));
      toast("Draft discarded", "success");
      router.push("/dashboard/tracker");
    } catch {
      toast("Failed to discard draft", "error");
    } finally {
      setDeleting(false);
    }
  };

  // ── Shared pre block styles ──
  const preStyle: React.CSSProperties = {
    fontSize: "0.8125rem",
    whiteSpace: "pre-wrap",
    background: "var(--bg-input)",
    padding: "var(--space-md)",
    borderRadius: "var(--radius-md)",
    maxHeight: 400,
    overflow: "auto",
    color: "var(--text-secondary)",
  };

  const sectionHeaderStyle: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    cursor: "pointer",
    userSelect: "none",
  };

  const h4Style: React.CSSProperties = {
    fontSize: "0.9375rem",
    fontWeight: 600,
    margin: 0,
  };

  // ── Loading state ──
  if (loading) {
    return (
      <div className="animate-fade-in" style={{ maxWidth: 800, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "var(--space-lg)" }} />
        <div className="skeleton" style={{ height: 200, marginBottom: "var(--space-md)" }} />
        <div className="skeleton" style={{ height: 200, marginBottom: "var(--space-md)" }} />
        <div className="skeleton" style={{ height: 120 }} />
      </div>
    );
  }

  // ── Error state ──
  if (error || !app) {
    return (
      <div className="animate-fade-in" style={{ maxWidth: 800, margin: "0 auto" }}>
        <div
          className="glass-card"
          style={{
            padding: "var(--space-2xl)",
            textAlign: "center",
            color: "var(--text-tertiary)",
          }}
        >
          <p style={{ fontSize: "2rem", marginBottom: "var(--space-sm)" }}>⚠️</p>
          <p>{error || "Application not found"}</p>
          <button
            className="btn btn-ghost"
            onClick={() => router.push("/dashboard/tracker")}
            style={{ marginTop: "var(--space-lg)" }}
          >
            ← Back to Tracker
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 800, margin: "0 auto", paddingBottom: 100 }}>
      {/* ──────── Header Section ──────── */}
      <div
        style={{
          marginBottom: "var(--space-xl)",
          display: "flex",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "var(--space-md)",
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "var(--space-xs)" }}>
            {app.company}
          </h1>
          <p style={{ fontSize: "1.125rem", color: "var(--text-secondary)", marginBottom: "var(--space-sm)" }}>
            {app.job_title}
          </p>
          {app.job_url && (
            <a
              href={app.job_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: "0.8125rem",
                color: "var(--accent)",
                textDecoration: "none",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
              onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}
            >
              🔗 View Job Posting
            </a>
          )}
        </div>

        <div style={{ display: "flex", gap: "var(--space-sm)", alignItems: "center", flexShrink: 0 }}>
          {/* Status badge */}
          <span
            className="badge badge-applied"
            style={{ textTransform: "capitalize" }}
          >
            {app.status || "draft"}
          </span>

          {/* Quality score badge */}
          {app.quality_score != null && (
            <span
              style={{
                display: "inline-block",
                padding: "0.25rem 0.75rem",
                borderRadius: "var(--radius-md)",
                fontSize: "0.875rem",
                fontWeight: 700,
                background: getScoreColor(app.quality_score).bg,
                color: getScoreColor(app.quality_score).color,
              }}
            >
              ⭐ {app.quality_score}/5
            </span>
          )}
        </div>
      </div>

      {/* ──────── Resume PDF Download ──────── */}
      {app.resume_pdf_url && (
        <div className="glass-card" style={{ padding: "var(--space-lg)", marginBottom: "var(--space-md)" }}>
          <button
            className="btn btn-ghost"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--space-sm)",
            }}
            onClick={async () => {
              try {
                const token = localStorage.getItem("jt_access_token") || "";
                const resp = await fetch(API_BASE + app.resume_pdf_url, {
                  headers: { Authorization: `Bearer ${token}` },
                });
                if (!resp.ok) throw new Error(`Download failed: ${resp.status}`);
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = app.resume_pdf_url?.split("/").pop() || "resume.pdf";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
              } catch {
                toast("Failed to download resume", "error");
              }
            }}
          >
            📄 Download Tailored Resume
          </button>
        </div>
      )}

      {/* ──────── Cover Letter (editable) ──────── */}
      <div className="glass-card" style={{ padding: "var(--space-lg)", marginBottom: "var(--space-md)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-sm)" }}>
          <h4 style={h4Style}>✉️ Cover Letter</h4>
          <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
            {coverLetter.length} chars
          </span>
        </div>
        <textarea
          className="input"
          value={coverLetter}
          onChange={(e) => setCoverLetter(e.target.value)}
          rows={12}
          style={{
            width: "100%",
            resize: "vertical",
            fontSize: "0.8125rem",
            lineHeight: 1.6,
          }}
          placeholder="Cover letter content..."
        />
      </div>

      {/* ──────── Tailored CV Bullets (editable) ──────── */}
      <div className="glass-card" style={{ padding: "var(--space-lg)", marginBottom: "var(--space-md)" }}>
        <h4 style={{ ...h4Style, marginBottom: "var(--space-sm)" }}>📝 Tailored CV Bullets</h4>
        <textarea
          className="input"
          value={tailoredBullets}
          onChange={(e) => setTailoredBullets(e.target.value)}
          rows={8}
          style={{
            width: "100%",
            resize: "vertical",
            fontSize: "0.8125rem",
            lineHeight: 1.6,
          }}
          placeholder="Tailored bullet points..."
        />
      </div>

      {/* ──────── LinkedIn DM (editable) ──────── */}
      <div className="glass-card" style={{ padding: "var(--space-lg)", marginBottom: "var(--space-md)" }}>
        <h4 style={{ ...h4Style, marginBottom: "var(--space-sm)" }}>💬 LinkedIn Outreach</h4>
        <textarea
          className="input"
          value={outreachDm}
          onChange={(e) => setOutreachDm(e.target.value)}
          rows={5}
          style={{
            width: "100%",
            resize: "vertical",
            fontSize: "0.8125rem",
            lineHeight: 1.6,
          }}
          placeholder="LinkedIn outreach message..."
        />
      </div>

      {/* ──────── Job Analysis (collapsible, read-only) ──────── */}
      {app.job_analysis && (
        <div className="glass-card" style={{ padding: "var(--space-lg)", marginBottom: "var(--space-md)" }}>
          <div
            style={sectionHeaderStyle}
            onClick={() => setShowJobAnalysis(!showJobAnalysis)}
          >
            <h4 style={h4Style}>📋 Job Analysis</h4>
            <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
              {showJobAnalysis ? "▼ Collapse" : "▶ Expand"}
            </span>
          </div>
          {showJobAnalysis && (
            <pre style={{ ...preStyle, marginTop: "var(--space-sm)" }}>
              {app.job_analysis}
            </pre>
          )}
        </div>
      )}

      {/* ──────── Company Research (collapsible, read-only) ──────── */}
      {app.company_profile && (
        <div className="glass-card" style={{ padding: "var(--space-lg)", marginBottom: "var(--space-md)" }}>
          <div
            style={sectionHeaderStyle}
            onClick={() => setShowCompanyResearch(!showCompanyResearch)}
          >
            <h4 style={h4Style}>🏢 Company Research</h4>
            <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
              {showCompanyResearch ? "▼ Collapse" : "▶ Expand"}
            </span>
          </div>
          {showCompanyResearch && (
            <pre style={{ ...preStyle, marginTop: "var(--space-sm)" }}>
              {app.company_profile}
            </pre>
          )}
        </div>
      )}

      {/* ──────── Role Fit (collapsible, read-only) ──────── */}
      {app.role_fit && (
        <div className="glass-card" style={{ padding: "var(--space-lg)", marginBottom: "var(--space-md)" }}>
          <div
            style={sectionHeaderStyle}
            onClick={() => setShowRoleFit(!showRoleFit)}
          >
            <h4 style={h4Style}>🎯 Role Fit Analysis</h4>
            <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
              {showRoleFit ? "▼ Collapse" : "▶ Expand"}
            </span>
          </div>
          {showRoleFit && (
            <pre style={{ ...preStyle, marginTop: "var(--space-sm)" }}>
              {app.role_fit}
            </pre>
          )}
        </div>
      )}

      {/* ──────── Quality Feedback ──────── */}
      {app.quality_feedback && (
        <div className="glass-card" style={{ padding: "var(--space-lg)", marginBottom: "var(--space-md)" }}>
          <h4 style={{ ...h4Style, marginBottom: "var(--space-sm)" }}>💡 Quality Feedback</h4>
          <pre style={preStyle}>{app.quality_feedback}</pre>
        </div>
      )}

      {/* ──────── Sticky Action Bar ──────── */}
      <div
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          padding: "var(--space-md) var(--space-xl)",
          background: "rgba(15, 15, 25, 0.85)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderTop: "1px solid rgba(255,255,255,0.08)",
          display: "flex",
          justifyContent: "center",
          gap: "var(--space-md)",
          alignItems: "center",
          zIndex: 100,
        }}
      >
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={submitting || deleting}
          style={{ fontSize: "0.875rem" }}
        >
          {submitting ? "⏳ Submitting..." : "✅ Submit Application"}
        </button>

        <button
          className="btn btn-ghost"
          onClick={handleDiscard}
          disabled={submitting || deleting}
          style={{ fontSize: "0.875rem", color: "var(--error, #f87171)" }}
        >
          {deleting ? "⏳ Deleting..." : "🗑️ Discard"}
        </button>

        <button
          className="btn btn-ghost"
          onClick={() => router.push("/dashboard/tracker")}
          style={{ fontSize: "0.875rem" }}
        >
          ← Back to Tracker
        </button>
      </div>
    </div>
  );
}
