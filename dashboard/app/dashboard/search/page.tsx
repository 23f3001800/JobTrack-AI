"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  runAgent,
  getApplications,
  discoverJobs,
  getProviders,
  getProfile,
  runBatch,
  type StreamStep,
  type BatchJob,
} from "@/lib/api";
import { useToast } from "@/components/Toast";

/**
 * Search & Apply Page — AI-powered job discovery + batch pipeline.
 *
 * 6 sections:
 * 1. Search Configuration — target role, provider, location, count
 * 2. Active Search Criteria — role & query pills shown during/after search
 * 3. Job Results — selectable cards with relevance/source badges
 * 4. Apply Controls — batch launcher with auto-mode toggle
 * 5. Pipeline Progress — streaming batch status with stats
 * 6. Manual URL Input — collapsible single-URL fallback
 */

/* ─── Icon mappings ─── */

const SOURCE_ICONS: Record<string, string> = {
  linkedin: "💼",
  indeed: "🔵",
  glassdoor: "🟢",
  lever: "⚡",
  greenhouse: "🌿",
  wellfound: "😇",
  workday: "🏢",
  naukri: "🇮🇳",
  smartrecruiters: "📋",
  taleo: "🏛️",
  ashby: "💎",
  himalayas: "🏔️",
  web: "🌐",
};

const STEP_ICONS: Record<string, string> = {
  "Job analysis": "🔍",
  "Company research": "🏢",
  "Role fit analysis": "🎯",
  "CV tailoring": "📝",
  "Cover letter": "✉️",
  "LinkedIn DM": "💬",
  "Resume PDF generated": "📄",
  "Application saved as draft": "✅",
  complete: "✅",
  error: "❌",
  batch_progress: "📊",
  job_complete: "✅",
  job_error: "❌",
  batch_complete: "🎉",
};

/* ─── Types ─── */

interface DiscoveredJob {
  title: string;
  company: string;
  url: string;
  location?: string;
  salary?: string;
  posted?: string;
  source?: string;
  relevance_score?: number;
  description?: string;
}

interface BatchStepUpdate {
  step?: string;
  status?: string;
  current?: number;
  total?: number;
  batch_index?: number;
  job_title?: string;
  job_company?: string;
  preview?: string;
  message?: string;
}

interface Provider {
  id: string;
  name: string;
}

interface SearchQuery {
  query: string;
  location?: string;
}

/* ─── Helpers ─── */

function relevanceBadge(score?: number) {
  if (score == null) return null;
  const pct = Math.round(score * (score <= 1 ? 100 : 1));
  let color = "var(--text-tertiary)";
  let bg = "rgba(255,255,255,0.06)";
  if (pct >= 80) {
    color = "#4ade80";
    bg = "rgba(74,222,128,0.12)";
  } else if (pct >= 60) {
    color = "#facc15";
    bg = "rgba(250,204,21,0.12)";
  }
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: "0.75rem",
        fontWeight: 700,
        color,
        background: bg,
        border: `1px solid ${color}33`,
      }}
    >
      {pct}% match
    </span>
  );
}

function Spinner({ size = 16 }: { size?: number }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        border: "2px solid transparent",
        borderTopColor: "currentColor",
        borderRadius: "50%",
        animation: "spin 0.6s linear infinite",
        flexShrink: 0,
      }}
    />
  );
}

/* ─── Role inference from skills + education ─── */

const ROLE_KEYWORDS: [string[], string][] = [
  [["data science", "machine learning", "ml", "deep learning", "pytorch", "tensorflow", "nlp"], "Data Scientist"],
  [["data engineer", "etl", "airflow", "spark", "data pipeline"], "Data Engineer"],
  [["data analyst", "tableau", "power bi", "analytics", "excel"], "Data Analyst"],
  [["frontend", "react", "vue", "angular", "next.js", "nextjs"], "Frontend Developer"],
  [["backend", "node.js", "express", "django", "flask", "fastapi"], "Backend Developer"],
  [["full stack", "fullstack", "mern", "mean"], "Full Stack Developer"],
  [["devops", "kubernetes", "docker", "ci/cd", "terraform", "aws"], "DevOps Engineer"],
  [["cloud", "aws", "azure", "gcp"], "Cloud Engineer"],
  [["android", "ios", "react native", "flutter", "mobile"], "Mobile Developer"],
  [["python", "java", "golang", "rust", "c++"], "Software Engineer"],
  [["product manager", "product management", "roadmap"], "Product Manager"],
  [["ui/ux", "ux", "figma", "design"], "UI/UX Designer"],
  [["cybersecurity", "security", "penetration"], "Security Engineer"],
  [["blockchain", "web3", "solidity"], "Blockchain Developer"],
];

function inferRoleTitle(
  skills: string[],
  education: Array<Record<string, string>>,
  summary: string
): string {
  const blob = [
    ...skills.map((s) => s.toLowerCase()),
    ...education.map((e) => (e.degree || "").toLowerCase()),
    summary.toLowerCase(),
  ].join(" ");

  for (const [keywords, role] of ROLE_KEYWORDS) {
    if (keywords.some((kw) => blob.includes(kw))) {
      return role;
    }
  }

  // Fallback: use degree field if present
  for (const edu of education) {
    const degree = edu.degree || "";
    if (degree.toLowerCase().includes("data science")) return "Data Scientist";
    if (degree.toLowerCase().includes("computer")) return "Software Engineer";
    if (degree) return `${degree.split(" ").slice(0, 3).join(" ")} Graduate`;
  }

  return "Software Engineer";
}

/* ─── Main Component ─── */

export default function SearchApplyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  /* ── Search configuration state ── */
  const [targetRole, setTargetRole] = useState("");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("auto");
  const [discoverLocation, setDiscoverLocation] = useState("");
  const [targetCount, setTargetCount] = useState(10);
  const [profileLoading, setProfileLoading] = useState(true);

  /* ── Discovery state ── */
  const [discovering, setDiscovering] = useState(false);
  const [queriesUsed, setQueriesUsed] = useState<SearchQuery[]>([]);
  const [jobs, setJobs] = useState<DiscoveredJob[]>([]);
  const [hasDiscovered, setHasDiscovered] = useState(false);

  /* ── Selection state ── */
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());

  /* ── Batch apply state ── */
  const [autoMode, setAutoMode] = useState(false);
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState(0);
  const [batchJobStatuses, setBatchJobStatuses] = useState<
    Map<number, { status: string; step: string; message?: string }>
  >(new Map());
  const [batchComplete, setBatchComplete] = useState(false);
  const [batchPrepared, setBatchPrepared] = useState(0);
  const [batchSubmitted, setBatchSubmitted] = useState(0);
  const [batchTotal, setBatchTotal] = useState(0);

  /* ── Manual URL state ── */
  const [manualOpen, setManualOpen] = useState(false);
  const initialUrl = searchParams.get("url") || "";
  const [jobUrl, setJobUrl] = useState(initialUrl);
  const [manualSteps, setManualSteps] = useState<StreamStep[]>([]);
  const [manualRunning, setManualRunning] = useState(false);
  const [manualError, setManualError] = useState("");
  const [draftId, setDraftId] = useState<string | null>(null);

  /* ── Load providers on mount ── */
  useEffect(() => {
    getProviders()
      .then((data) =>
        setProviders((data.providers || []) as unknown as Provider[])
      )
      .catch(() => {});
  }, []);

  /* ── Pre-fill target role from profile on mount ── */
  useEffect(() => {
    getProfile()
      .then((raw) => {
        const data = raw as Record<string, unknown>;
        const pp = (data as Record<string, unknown>).parsed_profile as
          | Record<string, unknown>
          | undefined;
        if (pp) {
          const exp = pp.experience as
            | Array<Record<string, string>>
            | undefined;
          if (exp && exp.length > 0 && exp[0].title) {
            setTargetRole(exp[0].title);
          } else {
            // Infer role from skills + education instead of raw summary
            const skills = (pp.skills as string[] | undefined) || [];
            const education = (pp.education as Array<Record<string, string>> | undefined) || [];
            const summary = String(pp.summary || "");

            const role = inferRoleTitle(skills, education, summary);
            setTargetRole(role);
          }
        }
      })
      .catch(() => {})
      .finally(() => setProfileLoading(false));
  }, []);

  /* ── If ?url= param present, open manual section ── */
  useEffect(() => {
    if (initialUrl) {
      setJobUrl(initialUrl);
      setManualOpen(true);
    }
  }, [initialUrl]);

  /* ─── Discovery handler ─── */
  const handleDiscover = async () => {
    if (!targetRole.trim()) {
      toast("Please enter a target role to search for", "error");
      return;
    }

    setDiscovering(true);
    setHasDiscovered(true);
    setJobs([]);
    setQueriesUsed([]);
    setSelected(new Set());
    setBatchComplete(false);
    setBatchJobStatuses(new Map());
    setBatchPrepared(0);
    setBatchSubmitted(0);

    try {
      const data = await discoverJobs(
        selectedProvider,
        discoverLocation.trim(),
        targetCount,
        targetRole.trim()
      );

      if (data.inferred_role) setTargetRole(data.inferred_role);

      if (data.error) {
        toast(data.error, "error");
        return;
      }

      const resultJobs = (data.results || []) as unknown as DiscoveredJob[];
      setJobs(resultJobs);
      setQueriesUsed(
        (data.queries_used || []) as unknown as SearchQuery[]
      );

      if (resultJobs.length === 0) {
        toast(
          "No matching jobs found — try a different role or location",
          "error"
        );
      }
    } catch {
      toast("Discovery failed — check your profile and try again", "error");
    } finally {
      setDiscovering(false);
    }
  };

  /* ─── Selection helpers ─── */
  const toggleSelect = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const selectAll = () => {
    setSelected(new Set(jobs.map((_, i) => i)));
  };

  const deselectAll = () => {
    setSelected(new Set());
  };

  const toggleExpand = (idx: number) => {
    setExpandedCards((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  /* ─── Batch apply handler ─── */
  const handleBatchApply = async () => {
    const selectedJobs = Array.from(selected).map((i) => jobs[i]);
    const count = Math.min(
      targetCount || selectedJobs.length,
      selectedJobs.length
    );
    const batch: BatchJob[] = selectedJobs.slice(0, count).map((j) => ({
      url: j.url,
      title: j.title,
      company: j.company || "",
      description: j.description || "",
    }));

    if (batch.length === 0) return;

    setBatchRunning(true);
    setBatchComplete(false);
    setBatchProgress(0);
    setBatchJobStatuses(new Map());
    setBatchPrepared(0);
    setBatchSubmitted(0);
    setBatchTotal(batch.length);

    try {
      await runBatch(batch, autoMode, (raw: Record<string, unknown>) => {
        const step = raw as unknown as BatchStepUpdate;

        /* Progress percentage from batch_progress events */
        if (step.step === "batch_progress" && step.current && step.total) {
          setBatchProgress(Math.round((step.current / step.total) * 100));
        }

        /* Track preparation — when Cover letter or CV tailoring completes */
        if (
          step.status === "done" &&
          (step.step === "Cover letter" ||
            step.step === "CV tailoring" ||
            step.step === "Resume PDF generated")
        ) {
          setBatchPrepared((prev) => prev + 1);
        }

        /* Track submission — job_complete means fully processed */
        if (step.step === "job_complete") {
          setBatchSubmitted((prev) => prev + 1);
          if (step.batch_index != null) {
            setBatchJobStatuses((prev) => {
              const next = new Map(prev);
              next.set(step.batch_index!, {
                status: "complete",
                step: "Complete",
                message: undefined,
              });
              return next;
            });
          }
        }

        /* Track errors */
        if (step.step === "job_error" && step.batch_index != null) {
          setBatchJobStatuses((prev) => {
            const next = new Map(prev);
            next.set(step.batch_index!, {
              status: "error",
              step: step.step || "Error",
              message: step.message,
            });
            return next;
          });
        }

        /* Per-job in-progress steps (e.g. Job analysis, Company research) */
        if (
          step.batch_index != null &&
          step.step !== "job_complete" &&
          step.step !== "job_error" &&
          step.step !== "batch_progress" &&
          step.step !== "batch_complete"
        ) {
          setBatchJobStatuses((prev) => {
            const next = new Map(prev);
            const existing = next.get(step.batch_index!);
            if (!existing || existing.status !== "complete") {
              next.set(step.batch_index!, {
                status: step.status || "running",
                step: step.step || "",
                message: step.preview || step.message,
              });
            }
            return next;
          });
        }

        /* Batch complete */
        if (step.step === "batch_complete") {
          setBatchComplete(true);
          setBatchProgress(100);
        }
      });
      setBatchComplete(true);
      setBatchProgress(100);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Batch pipeline failed";
      toast(msg, "error");
    } finally {
      setBatchRunning(false);
    }
  };

  /* ─── Manual agent runner ─── */
  const handleManualRun = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!jobUrl.trim()) return;

    setManualError("");
    setManualSteps([]);
    setManualRunning(true);
    setDraftId(null);

    try {
      await runAgent(jobUrl.trim(), "", (step) => {
        setManualSteps((prev) => [...prev, step]);
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Pipeline failed";
      setManualError(message);
    } finally {
      setManualRunning(false);
    }
  };

  const manualComplete = manualSteps.some((s) => s.step === "complete");

  useEffect(() => {
    if (manualComplete) {
      getApplications()
        .then((data) => {
          const apps = data.applications || [];
          if (apps.length > 0) setDraftId(String(apps.length - 1));
        })
        .catch(() => {});
    }
  }, [manualComplete]);

  /* ─── Derived values ─── */
  const selectedCount = selected.size;
  const applyCount = Math.min(selectedCount, targetCount);
  const showBatchProgress = batchRunning || batchComplete;
  const batchRemaining = batchTotal - batchSubmitted;

  return (
    <div className="animate-fade-in">
      {/* ═══════════ Page Header ═══════════ */}
      <div className="page-header">
        <h1>🔍 Search & Apply</h1>
        <p>AI discovers jobs from your resume, then applies in batch</p>
      </div>

      {/* ═══════════ Section 1: Search Configuration ═══════════ */}
      <div
        className="glass-card"
        style={{
          padding: "var(--space-xl)",
          maxWidth: 800,
          marginBottom: "var(--space-xl)",
        }}
      >
        <h2
          style={{
            fontSize: "1.125rem",
            fontWeight: 700,
            marginBottom: "var(--space-lg)",
            display: "flex",
            alignItems: "center",
            gap: "var(--space-sm)",
          }}
        >
          <span style={{ fontSize: "1.25rem" }}>🎯</span>
          Search Configuration
        </h2>

        {/* Row 1: Target Role */}
        <div style={{ marginBottom: "var(--space-lg)" }}>
          <label className="input-label" htmlFor="target-role">
            Target Role
          </label>
          {profileLoading ? (
            <div
              className="skeleton"
              style={{ height: 42, borderRadius: 8 }}
            />
          ) : (
            <input
              id="target-role"
              className="input"
              type="text"
              placeholder="e.g. Senior Frontend Engineer, Product Manager..."
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
              disabled={discovering}
              style={{ fontSize: "0.9375rem" }}
            />
          )}
          <p
            style={{
              fontSize: "0.7rem",
              color: "var(--text-tertiary)",
              marginTop: 4,
              opacity: 0.8,
            }}
          >
            Pre-filled from your resume · Edit to refine your search
          </p>
        </div>

        {/* Row 2: Provider + Location */}
        <div
          style={{
            display: "flex",
            gap: "var(--space-md)",
            flexWrap: "wrap",
            marginBottom: "var(--space-lg)",
          }}
        >
          {/* Provider selector */}
          <div style={{ flex: "1 1 200px" }}>
            <label className="input-label" htmlFor="provider-select">
              Search Provider
            </label>
            <select
              id="provider-select"
              className="input"
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              disabled={discovering}
              style={{ cursor: "pointer" }}
            >
              <option value="auto">🤖 Auto (best available)</option>
              {providers.map((p: Provider) => (
                <option key={p.id} value={p.id}>
                  {SOURCE_ICONS[p.id] || "🌐"} {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Location input */}
          <div style={{ flex: "1 1 200px" }}>
            <label className="input-label" htmlFor="discover-location">
              Location (optional)
            </label>
            <input
              id="discover-location"
              className="input"
              type="text"
              placeholder="Remote, San Francisco, London..."
              value={discoverLocation}
              onChange={(e) => setDiscoverLocation(e.target.value)}
              disabled={discovering}
            />
          </div>
        </div>

        {/* Row 3: Number of Applications */}
        <div style={{ marginBottom: "var(--space-lg)" }}>
          <label className="input-label" htmlFor="target-count">
            Number of applications to process
          </label>
          <input
            id="target-count"
            className="input"
            type="number"
            min={1}
            max={25}
            value={targetCount}
            onChange={(e) =>
              setTargetCount(
                Math.min(25, Math.max(1, Number(e.target.value) || 1))
              )
            }
            disabled={discovering}
            style={{ maxWidth: 160 }}
          />
          <p
            style={{
              fontSize: "0.7rem",
              color: "var(--text-tertiary)",
              marginTop: 4,
              opacity: 0.8,
            }}
          >
            Each job URL = 1 tailored application
          </p>
        </div>

        {/* Discover button */}
        <button
          className="btn btn-primary"
          onClick={handleDiscover}
          disabled={discovering || !targetRole.trim()}
          style={{
            width: "100%",
            padding: "0.875rem",
            fontSize: "1rem",
            fontWeight: 700,
            letterSpacing: "0.01em",
          }}
        >
          {discovering ? (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Spinner />
              Discovering jobs from your resume...
            </span>
          ) : (
            `🔍 Discover ${targetCount} Matching Jobs`
          )}
        </button>
      </div>

      {/* ═══════════ Section 2: Active Search Criteria ═══════════ */}
      {hasDiscovered && (
        <div
          style={{
            maxWidth: 800,
            marginBottom: "var(--space-lg)",
          }}
        >
          <div
            className="glass-card"
            style={{
              padding: "var(--space-md) var(--space-lg)",
              background: "rgba(99,102,241,0.04)",
            }}
          >
            {/* Search criteria row */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-lg)",
                flexWrap: "wrap",
                marginBottom: queriesUsed.length > 0 ? "var(--space-md)" : 0,
              }}
            >
              <span
                style={{
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                }}
              >
                Searching as:{" "}
                <strong style={{ color: "var(--accent)" }}>
                  {targetRole}
                </strong>
              </span>
              <span
                style={{
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                }}
              >
                Target:{" "}
                <strong style={{ color: "var(--accent)" }}>
                  {targetCount} applications
                </strong>
              </span>
            </div>

            {/* Query pills */}
            {queriesUsed.length > 0 && (
              <div>
                <span
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--text-tertiary)",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Auto-generated queries from your resume:
                </span>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "var(--space-xs)",
                    marginTop: "var(--space-xs)",
                  }}
                >
                  {queriesUsed.map((q: SearchQuery, i: number) => (
                    <span
                      key={i}
                      style={{
                        display: "inline-block",
                        padding: "3px 12px",
                        borderRadius: 999,
                        fontSize: "0.75rem",
                        fontWeight: 500,
                        background: "var(--accent)",
                        color: "#fff",
                        opacity: 0.9,
                      }}
                    >
                      {typeof q === "string"
                        ? q
                        : q.query || JSON.stringify(q)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══════════ Loading Skeletons ═══════════ */}
      {discovering && (
        <div style={{ maxWidth: 800, marginBottom: "var(--space-xl)" }}>
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="skeleton"
              style={{
                height: 120,
                marginBottom: "var(--space-md)",
                borderRadius: 12,
              }}
            />
          ))}
        </div>
      )}

      {/* ═══════════ Empty State ═══════════ */}
      {!discovering && hasDiscovered && jobs.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "var(--space-2xl)",
            color: "var(--text-tertiary)",
            maxWidth: 800,
          }}
        >
          <p style={{ fontSize: "2.5rem", marginBottom: "var(--space-sm)" }}>
            🔍
          </p>
          <p style={{ fontSize: "0.9375rem" }}>
            No matching jobs found. Try a different role, provider, or
            location.
          </p>
        </div>
      )}

      {/* ═══════════ Section 3: Job Results ═══════════ */}
      {!discovering && jobs.length > 0 && !showBatchProgress && (
        <div style={{ maxWidth: 800, marginBottom: "var(--space-xl)" }}>
          {/* Results header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "var(--space-md)",
              flexWrap: "wrap",
              gap: "var(--space-sm)",
            }}
          >
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: 600,
                margin: 0,
              }}
            >
              Found{" "}
              <span style={{ color: "var(--accent)" }}>
                {jobs.length}
              </span>{" "}
              matching jobs
            </h2>
            <div
              style={{
                display: "flex",
                gap: "var(--space-sm)",
                alignItems: "center",
              }}
            >
              <button
                className="btn btn-ghost"
                onClick={selectAll}
                style={{ fontSize: "0.8125rem" }}
              >
                Select all
              </button>
              <button
                className="btn btn-ghost"
                onClick={deselectAll}
                style={{ fontSize: "0.8125rem" }}
              >
                Deselect all
              </button>
              {selectedCount > 0 && (
                <span
                  style={{
                    fontSize: "0.8125rem",
                    fontWeight: 700,
                    color: "var(--accent)",
                    padding: "4px 12px",
                    borderRadius: 999,
                    background: "rgba(99,102,241,0.12)",
                  }}
                >
                  {selectedCount} job{selectedCount !== 1 ? "s" : ""}{" "}
                  selected
                </span>
              )}
            </div>
          </div>

          {/* Job cards */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-md)",
            }}
          >
            {jobs.map((job, i) => {
              const isSelected = selected.has(i);
              const isExpanded = expandedCards.has(i);
              return (
                <div
                  key={i}
                  className="glass-card"
                  style={{
                    padding: "var(--space-lg)",
                    borderColor: isSelected ? "var(--accent)" : undefined,
                    boxShadow: isSelected
                      ? "0 0 0 1px var(--accent), 0 4px 24px rgba(99,102,241,0.08)"
                      : undefined,
                    transition: "border-color 0.2s, box-shadow 0.2s",
                    cursor: "pointer",
                  }}
                  onClick={() => toggleSelect(i)}
                >
                  <div
                    style={{
                      display: "flex",
                      gap: "var(--space-md)",
                      alignItems: "flex-start",
                    }}
                  >
                    {/* Checkbox */}
                    <div
                      style={{
                        width: 22,
                        height: 22,
                        borderRadius: 6,
                        border: `2px solid ${
                          isSelected ? "var(--accent)" : "var(--border)"
                        }`,
                        background: isSelected
                          ? "var(--accent)"
                          : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        marginTop: 2,
                        transition: "all 0.15s",
                      }}
                    >
                      {isSelected && (
                        <span
                          style={{
                            color: "#fff",
                            fontSize: "0.75rem",
                            lineHeight: 1,
                          }}
                        >
                          ✓
                        </span>
                      )}
                    </div>

                    {/* Job info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      {/* Top row: badges */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "var(--space-sm)",
                          marginBottom: "var(--space-xs)",
                          flexWrap: "wrap",
                        }}
                      >
                        {relevanceBadge(job.relevance_score)}
                        {job.source && (
                          <span
                            className="badge badge-applied"
                            style={{
                              textTransform: "capitalize",
                              fontSize: "0.6875rem",
                            }}
                          >
                            {SOURCE_ICONS[job.source] || "🌐"}{" "}
                            {job.source}
                          </span>
                        )}
                      </div>

                      {/* Title */}
                      <h3
                        style={{
                          fontSize: "0.9375rem",
                          fontWeight: 700,
                          marginBottom: 2,
                          lineHeight: 1.3,
                        }}
                      >
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            color: "inherit",
                            textDecoration: "none",
                          }}
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.textDecoration =
                              "underline")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.textDecoration = "none")
                          }
                        >
                          {job.title}
                        </a>
                      </h3>

                      {/* Company + meta */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "var(--space-md)",
                          fontSize: "0.8125rem",
                          color: "var(--text-secondary)",
                          flexWrap: "wrap",
                          marginTop: 2,
                        }}
                      >
                        {job.company && <span>🏢 {job.company}</span>}
                        {job.location && <span>📍 {job.location}</span>}
                        {job.posted && <span>🕐 {job.posted}</span>}
                      </div>

                      {/* Salary — prominent row */}
                      {job.salary && (
                        <div
                          style={{
                            marginTop: "var(--space-xs)",
                            padding: "4px 12px",
                            borderRadius: 8,
                            background: "rgba(74,222,128,0.08)",
                            border: "1px solid rgba(74,222,128,0.2)",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            fontSize: "0.8125rem",
                            fontWeight: 600,
                            color: "#4ade80",
                          }}
                        >
                          💰 {job.salary}
                        </div>
                      )}

                      {/* Expandable description */}
                      {job.description && (
                        <div style={{ marginTop: "var(--space-sm)" }}>
                          <button
                            className="btn btn-ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleExpand(i);
                            }}
                            style={{
                              fontSize: "0.75rem",
                              padding: "2px 8px",
                              opacity: 0.7,
                            }}
                          >
                            {isExpanded
                              ? "▼ Hide details"
                              : "▶ Show details"}
                          </button>
                          <div
                            style={{
                              maxHeight: isExpanded ? 300 : 0,
                              overflow: "hidden",
                              transition: "max-height 0.3s ease",
                            }}
                          >
                            <p
                              style={{
                                fontSize: "0.8125rem",
                                color: "var(--text-secondary)",
                                lineHeight: 1.6,
                                marginTop: "var(--space-xs)",
                                whiteSpace: "pre-wrap",
                                maxHeight: 280,
                                overflowY: "auto",
                              }}
                            >
                              {job.description}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* External link */}
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Open job posting"
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        fontSize: "1.125rem",
                        opacity: 0.5,
                        transition: "opacity 0.15s",
                        flexShrink: 0,
                      }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.opacity = "1")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.opacity = "0.5")
                      }
                    >
                      🔗
                    </a>
                  </div>
                </div>
              );
            })}
          </div>

          {/* ═══════════ Section 4: Apply Controls ═══════════ */}
          {selectedCount > 0 && (
            <div
              className="glass-card"
              style={{
                padding: "var(--space-xl)",
                marginTop: "var(--space-xl)",
                background:
                  "linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(139,92,246,0.04) 100%)",
              }}
            >
              <h2
                style={{
                  fontSize: "1.125rem",
                  fontWeight: 700,
                  marginBottom: "var(--space-md)",
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-sm)",
                }}
              >
                <span style={{ fontSize: "1.25rem" }}>🚀</span>
                Apply to Selected Jobs
              </h2>

              {/* Summary stats */}
              <p
                style={{
                  fontSize: "0.875rem",
                  color: "var(--text-secondary)",
                  marginBottom: "var(--space-lg)",
                }}
              >
                <strong style={{ color: "var(--accent)" }}>
                  {selectedCount}
                </strong>{" "}
                jobs selected ·{" "}
                <strong style={{ color: "var(--accent)" }}>
                  {applyCount}
                </strong>{" "}
                to apply
              </p>

              {/* Auto mode toggle */}
              <div style={{ marginBottom: "var(--space-lg)" }}>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-sm)",
                    cursor: "pointer",
                    fontSize: "0.875rem",
                    userSelect: "none",
                  }}
                >
                  <div
                    onClick={() => setAutoMode(!autoMode)}
                    style={{
                      width: 44,
                      height: 24,
                      borderRadius: 12,
                      background: autoMode
                        ? "var(--accent)"
                        : "var(--border)",
                      position: "relative",
                      transition: "background 0.2s",
                      cursor: "pointer",
                      flexShrink: 0,
                    }}
                  >
                    <div
                      style={{
                        width: 18,
                        height: 18,
                        borderRadius: "50%",
                        background: "#fff",
                        position: "absolute",
                        top: 3,
                        left: autoMode ? 23 : 3,
                        transition: "left 0.2s",
                      }}
                    />
                  </div>
                  <span>
                    ⚡ Auto Mode{" "}
                    <span
                      style={{
                        color: "var(--text-tertiary)",
                        fontSize: "0.75rem",
                      }}
                    >
                      — submit without review
                    </span>
                  </span>
                </label>
              </div>

              {/* Apply button */}
              <button
                className="btn btn-primary"
                onClick={handleBatchApply}
                disabled={batchRunning}
                style={{
                  width: "100%",
                  padding: "0.875rem",
                  fontSize: "1rem",
                  fontWeight: 700,
                }}
              >
                {batchRunning ? (
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <Spinner />
                    Pipeline running...
                  </span>
                ) : (
                  `🚀 Apply to ${applyCount} Job${
                    applyCount !== 1 ? "s" : ""
                  } — ${applyCount} Tailored Application${
                    applyCount !== 1 ? "s" : ""
                  }`
                )}
              </button>

              {/* Helper text */}
              <p
                style={{
                  fontSize: "0.7rem",
                  color: "var(--text-tertiary)",
                  textAlign: "center",
                  marginTop: "var(--space-sm)",
                  opacity: 0.8,
                }}
              >
                Each job receives its own tailored resume and cover letter
              </p>
            </div>
          )}
        </div>
      )}

      {/* ═══════════ Section 5: Pipeline Progress ═══════════ */}
      {showBatchProgress && (
        <div style={{ maxWidth: 800, marginBottom: "var(--space-xl)" }}>
          <div
            className="glass-card"
            style={{ padding: "var(--space-xl)" }}
          >
            {/* Header */}
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: 700,
                marginBottom: "var(--space-lg)",
              }}
            >
              {batchComplete
                ? "🎉 Batch Complete — All applications processed"
                : "⏳ Batch Pipeline in Progress"}
            </h2>

            {/* Stats row */}
            <div
              style={{
                display: "flex",
                gap: "var(--space-md)",
                flexWrap: "wrap",
                marginBottom: "var(--space-lg)",
              }}
            >
              {/* Target Role */}
              <div
                style={{
                  flex: "1 1 140px",
                  padding: "var(--space-md)",
                  borderRadius: 10,
                  background: "rgba(99,102,241,0.06)",
                  border: "1px solid rgba(99,102,241,0.15)",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "1.25rem",
                    marginBottom: 4,
                  }}
                >
                  🎯
                </div>
                <div
                  style={{
                    fontSize: "0.6875rem",
                    color: "var(--text-tertiary)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    fontWeight: 600,
                    marginBottom: 2,
                  }}
                >
                  Target Role
                </div>
                <div
                  style={{
                    fontSize: "0.8125rem",
                    fontWeight: 700,
                    color: "var(--accent)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {targetRole || "—"}
                </div>
              </div>

              {/* Jobs Discovered */}
              <div
                style={{
                  flex: "1 1 100px",
                  padding: "var(--space-md)",
                  borderRadius: 10,
                  background: "rgba(99,102,241,0.06)",
                  border: "1px solid rgba(99,102,241,0.15)",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "1.25rem",
                    marginBottom: 4,
                  }}
                >
                  🔍
                </div>
                <div
                  style={{
                    fontSize: "0.6875rem",
                    color: "var(--text-tertiary)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    fontWeight: 600,
                    marginBottom: 2,
                  }}
                >
                  Discovered
                </div>
                <div
                  style={{
                    fontSize: "1.25rem",
                    fontWeight: 700,
                  }}
                >
                  {jobs.length}
                </div>
              </div>

              {/* Applications Prepared */}
              <div
                style={{
                  flex: "1 1 100px",
                  padding: "var(--space-md)",
                  borderRadius: 10,
                  background: "rgba(250,204,21,0.06)",
                  border: "1px solid rgba(250,204,21,0.15)",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "1.25rem",
                    marginBottom: 4,
                  }}
                >
                  📝
                </div>
                <div
                  style={{
                    fontSize: "0.6875rem",
                    color: "var(--text-tertiary)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    fontWeight: 600,
                    marginBottom: 2,
                  }}
                >
                  Prepared
                </div>
                <div
                  style={{
                    fontSize: "1.25rem",
                    fontWeight: 700,
                    color: "#facc15",
                  }}
                >
                  {batchPrepared}
                </div>
              </div>

              {/* Applications Submitted */}
              <div
                style={{
                  flex: "1 1 100px",
                  padding: "var(--space-md)",
                  borderRadius: 10,
                  background: "rgba(74,222,128,0.06)",
                  border: "1px solid rgba(74,222,128,0.15)",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "1.25rem",
                    marginBottom: 4,
                  }}
                >
                  ✅
                </div>
                <div
                  style={{
                    fontSize: "0.6875rem",
                    color: "var(--text-tertiary)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    fontWeight: 600,
                    marginBottom: 2,
                  }}
                >
                  Submitted
                </div>
                <div
                  style={{
                    fontSize: "1.25rem",
                    fontWeight: 700,
                    color: "#4ade80",
                  }}
                >
                  {batchSubmitted}
                </div>
              </div>

              {/* Remaining */}
              <div
                style={{
                  flex: "1 1 100px",
                  padding: "var(--space-md)",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid var(--border)",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "1.25rem",
                    marginBottom: 4,
                  }}
                >
                  ⏳
                </div>
                <div
                  style={{
                    fontSize: "0.6875rem",
                    color: "var(--text-tertiary)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    fontWeight: 600,
                    marginBottom: 2,
                  }}
                >
                  Remaining
                </div>
                <div
                  style={{
                    fontSize: "1.25rem",
                    fontWeight: 700,
                    color: batchRemaining > 0 ? "var(--text-secondary)" : "#4ade80",
                  }}
                >
                  {batchRemaining}
                </div>
              </div>
            </div>

            {/* Progress bar */}
            <div
              style={{
                width: "100%",
                height: 8,
                background: "var(--border)",
                borderRadius: 4,
                overflow: "hidden",
                marginBottom: "var(--space-lg)",
              }}
            >
              <div
                style={{
                  width: `${batchProgress}%`,
                  height: "100%",
                  background: batchComplete
                    ? "linear-gradient(90deg, #4ade80, #22d3ee)"
                    : "linear-gradient(90deg, var(--accent), #8b5cf6)",
                  borderRadius: 4,
                  transition: "width 0.4s ease",
                }}
              />
            </div>

            {/* Per-job status list */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-sm)",
              }}
            >
              {Array.from(selected)
                .slice(0, applyCount || selected.size)
                .map((jobIdx, i) => {
                  const job = jobs[jobIdx];
                  const status = batchJobStatuses.get(i);
                  let icon = "⏸️";
                  let statusColor = "var(--text-tertiary)";
                  if (status) {
                    if (
                      status.status === "complete" ||
                      status.status === "done"
                    ) {
                      icon = "✅";
                      statusColor = "#4ade80";
                    } else if (
                      status.status === "running" ||
                      status.status === "in_progress"
                    ) {
                      icon = "⏳";
                      statusColor = "var(--accent)";
                    } else if (status.status === "error") {
                      icon = "❌";
                      statusColor = "#f87171";
                    }
                  }

                  return (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "var(--space-md)",
                        padding: "var(--space-sm) var(--space-md)",
                        borderRadius: 8,
                        background: "rgba(255,255,255,0.02)",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "1.125rem",
                          flexShrink: 0,
                        }}
                      >
                        {icon}
                      </span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: "0.875rem",
                            fontWeight: 600,
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {job?.title || `Job #${i + 1}`}
                        </div>
                        <div
                          style={{
                            fontSize: "0.75rem",
                            color: statusColor,
                          }}
                        >
                          {status
                            ? STEP_ICONS[status.step] ||
                              STEP_ICONS[status.status] ||
                              ""
                            : ""}{" "}
                          {status
                            ? status.step || status.status
                            : "Queued"}
                          {status?.message && ` — ${status.message}`}
                        </div>
                      </div>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-tertiary)",
                          flexShrink: 0,
                        }}
                      >
                        {job?.company}
                      </span>
                    </div>
                  );
                })}
            </div>

            {/* Completion actions */}
            {batchComplete && (
              <div
                style={{
                  display: "flex",
                  gap: "var(--space-md)",
                  marginTop: "var(--space-xl)",
                  flexWrap: "wrap",
                }}
              >
                <button
                  className="btn btn-primary"
                  onClick={() => router.push("/dashboard/tracker")}
                >
                  📋 View All Drafts in Tracker
                </button>
                <button
                  className="btn btn-ghost"
                  onClick={() => {
                    setBatchComplete(false);
                    setBatchJobStatuses(new Map());
                    setBatchProgress(0);
                    setBatchPrepared(0);
                    setBatchSubmitted(0);
                    setBatchTotal(0);
                  }}
                >
                  🔍 Back to Results
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══════════ Section 6: Manual URL Input ═══════════ */}
      <div style={{ maxWidth: 800 }}>
        <button
          className="btn btn-ghost"
          onClick={() => setManualOpen(!manualOpen)}
          style={{
            width: "100%",
            textAlign: "left",
            padding: "var(--space-md) var(--space-lg)",
            fontSize: "0.9375rem",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: "var(--space-sm)",
            borderRadius: 12,
            border: "1px solid var(--border)",
            marginBottom: "var(--space-md)",
          }}
        >
          <span>{manualOpen ? "▼" : "▶"}</span>
          <span>📎 Or paste a job URL directly</span>
        </button>

        <div
          style={{
            maxHeight: manualOpen ? 800 : 0,
            overflow: "hidden",
            transition: "max-height 0.35s ease",
          }}
        >
          <div
            className="glass-card"
            style={{ padding: "var(--space-xl)" }}
          >
            <form onSubmit={handleManualRun}>
              <div style={{ marginBottom: "var(--space-lg)" }}>
                <label
                  className="input-label"
                  htmlFor="manual-job-url"
                >
                  Job Posting URL
                </label>
                <input
                  id="manual-job-url"
                  className="input"
                  type="url"
                  placeholder="https://linkedin.com/jobs/view/..."
                  value={jobUrl}
                  onChange={(e) => setJobUrl(e.target.value)}
                  required
                  disabled={manualRunning}
                />
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-tertiary)",
                    marginTop: "var(--space-xs)",
                  }}
                >
                  Your profile and resume from Settings will be used
                  automatically.
                </p>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={manualRunning || !jobUrl.trim()}
                style={{ width: "100%" }}
              >
                {manualRunning ? (
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <Spinner />
                    Agents working...
                  </span>
                ) : (
                  "🚀 Apply with AI"
                )}
              </button>
            </form>

            {/* Manual error */}
            {manualError && (
              <div
                className="error-msg"
                style={{ marginTop: "var(--space-md)" }}
              >
                {manualError}
              </div>
            )}

            {/* Manual streaming progress */}
            {manualSteps.length > 0 && (
              <div style={{ marginTop: "var(--space-xl)" }}>
                <h3
                  style={{
                    fontSize: "1rem",
                    fontWeight: 600,
                    marginBottom: "var(--space-md)",
                  }}
                >
                  {manualComplete
                    ? "✅ Application materials ready for review"
                    : "⏳ Agent Progress"}
                </h3>

                <div className="stream-steps">
                  {manualSteps.map((step, i) => (
                    <div className="stream-step" key={i}>
                      <div
                        className={`step-icon ${
                          step.status === "done" ? "done" : "loading"
                        }`}
                      >
                        {STEP_ICONS[step.step] || "⚡"}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="step-label">{step.step}</div>
                        {step.preview && (
                          <div className="step-preview">
                            {step.preview}
                          </div>
                        )}
                        {step.message && (
                          <div
                            className="step-preview"
                            style={{
                              color: "var(--quality-low)",
                            }}
                          >
                            {step.message}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {manualRunning && (
                    <div className="stream-step">
                      <div className="step-icon loading">⏳</div>
                      <div style={{ flex: 1 }}>
                        <div
                          className="step-label"
                          style={{
                            color: "var(--text-secondary)",
                          }}
                        >
                          Waiting for next agent...
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {manualComplete && (
                  <div
                    style={{
                      display: "flex",
                      gap: "var(--space-md)",
                      marginTop: "var(--space-xl)",
                    }}
                  >
                    <button
                      className="btn btn-primary"
                      onClick={() =>
                        router.push(
                          draftId
                            ? `/dashboard/review/${draftId}`
                            : "/dashboard/tracker"
                        )
                      }
                    >
                      📋 Review & Submit
                    </button>
                    <button
                      className="btn btn-ghost"
                      onClick={() => {
                        setManualSteps([]);
                        setJobUrl("");
                        setManualError("");
                        setDraftId(null);
                      }}
                    >
                      🚀 Run Another
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Spinner keyframe */}
      <style jsx>{`
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}
