"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { searchJobs, runAgent, getApplications, type StreamStep } from "@/lib/api";
import { useToast } from "@/components/Toast";

/**
 * Unified Search & Apply Page — discover jobs + run the AI agent.
 *
 * WHY merge search and apply into one page?
 * Users flow naturally from searching → picking a job → applying.
 * A single page with tab toggle removes friction. Clicking "Apply"
 * on a search result switches to apply mode with the URL pre-filled.
 *
 * Modes:
 * - search: keyword + location search with result cards
 * - apply:  paste/pre-fill a job URL and run the multi-agent pipeline
 */

/** Source platform → emoji icon mapping */
const SOURCE_ICONS: Record<string, string> = {
  linkedin: "💼",
  indeed: "🔵",
  glassdoor: "🟢",
  lever: "⚡",
  greenhouse: "🌿",
  wellfound: "😇",
  workday: "🏢",
  web: "🌐",
};

/** Map agent step names to emoji icons */
const STEP_ICONS: Record<string, string> = {
  scraping: "🔍",
  researching: "🏢",
  writing: "✍️",
  quality: "⭐",
  "Job analysis": "🔍",
  "Company research": "🏢",
  "Role fit analysis": "🎯",
  "CV tailoring": "📝",
  "Cover letter": "✉️",
  "LinkedIn DM": "💬",
  "Application logged": "✅",
  complete: "✅",
  error: "❌",
};

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source: string;
}

export default function SearchApplyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  // Determine initial mode from ?mode= query param
  const initialMode = searchParams.get("mode") === "apply" ? "apply" : "search";
  const initialUrl = searchParams.get("url") || "";

  const [mode, setMode] = useState<"search" | "apply">(initialMode as "search" | "apply");

  // ── Search state ──
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  // ── Apply state ──
  const [jobUrl, setJobUrl] = useState(initialUrl);
  const [steps, setSteps] = useState<StreamStep[]>([]);
  const [running, setRunning] = useState(false);
  const [agentError, setAgentError] = useState("");
  const [autoRun, setAutoRun] = useState(false);
  const [draftId, setDraftId] = useState<string | null>(null);

  // Sync URL param on mount
  useEffect(() => {
    if (initialUrl) {
      setJobUrl(initialUrl);
      setMode("apply");
    }
  }, [initialUrl]);

  // ── Search handler ──
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSearchLoading(true);
    setSearched(true);

    try {
      const data = await searchJobs(query.trim(), location.trim(), 15);
      setResults(data.results || []);
    } catch {
      setResults([]);
      toast("Search failed — try again", "error");
    } finally {
      setSearchLoading(false);
    }
  };

  /** Switch to apply mode, pre-fill URL, and auto-start agent */
  const handleApplyFromResult = (url: string) => {
    setJobUrl(url);
    setMode("apply");
    setSteps([]);
    setAgentError("");
    setAutoRun(true);
  };

  // Auto-run agent when triggered from search results
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (autoRun && jobUrl && !running) {
      setAutoRun(false);
      handleRunAgent();
    }
  }, [autoRun, jobUrl]);

  // ── Agent runner ──
  const handleRunAgent = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!jobUrl.trim()) return;

    setAgentError("");
    setSteps([]);
    setRunning(true);

    try {
      await runAgent(
        jobUrl.trim(),
        "", // Empty — backend auto-fetches profile
        (step) => {
          setSteps((prev) => [...prev, step]);
        }
      );
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Pipeline failed";
      setAgentError(message);
    } finally {
      setRunning(false);
    }
  };

  const isComplete = steps.some((s) => s.step === "complete");

  // After pipeline completes, find the new draft for review link
  useEffect(() => {
    if (isComplete) {
      getApplications().then((data) => {
        const apps = data.applications || [];
        if (apps.length > 0) {
          setDraftId(String(apps.length - 1));
        }
      }).catch(() => {});
    }
  }, [isComplete]);

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <h1>🔍 Search & Apply</h1>
        <p>Discover jobs and apply with AI-powered materials</p>
      </div>

      {/* ──────── Tab Toggle ──────── */}
      <div
        style={{
          display: "flex",
          gap: "var(--space-sm)",
          marginBottom: "var(--space-xl)",
        }}
      >
        <button
          className={`btn ${mode === "search" ? "btn-primary" : "btn-ghost"}`}
          onClick={() => setMode("search")}
          disabled={running}
        >
          🔍 Search Jobs
        </button>
        <button
          className={`btn ${mode === "apply" ? "btn-primary" : "btn-ghost"}`}
          onClick={() => setMode("apply")}
          disabled={running}
        >
          🚀 Apply to Job
        </button>
      </div>

      {/* ──────── SEARCH MODE ──────── */}
      {mode === "search" && (
        <>
          {/* Search form */}
          <div
            className="glass-card"
            style={{ padding: "var(--space-xl)", maxWidth: 700 }}
          >
            <form
              onSubmit={handleSearch}
              style={{
                display: "flex",
                gap: "var(--space-md)",
                flexWrap: "wrap",
              }}
            >
              <div style={{ flex: "2 1 250px" }}>
                <label className="input-label" htmlFor="search-query">
                  Keywords
                </label>
                <input
                  id="search-query"
                  className="input"
                  type="text"
                  placeholder="Python AI engineer, React developer..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  required
                  disabled={searchLoading}
                />
              </div>

              <div style={{ flex: "1 1 150px" }}>
                <label className="input-label" htmlFor="search-location">
                  Location
                </label>
                <input
                  id="search-location"
                  className="input"
                  type="text"
                  placeholder="Remote, London..."
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  disabled={searchLoading}
                />
              </div>

              <div
                style={{
                  flex: "0 0 auto",
                  display: "flex",
                  alignItems: "flex-end",
                }}
              >
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={searchLoading || !query.trim()}
                >
                  {searchLoading ? "Searching..." : "🔍 Search"}
                </button>
              </div>
            </form>
          </div>

          {/* Search results */}
          {searchLoading && (
            <div style={{ marginTop: "var(--space-xl)" }}>
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="skeleton"
                  style={{
                    height: 100,
                    marginBottom: "var(--space-md)",
                    maxWidth: 700,
                  }}
                />
              ))}
            </div>
          )}

          {!searchLoading && searched && results.length === 0 && (
            <div
              style={{
                textAlign: "center",
                padding: "var(--space-2xl)",
                color: "var(--text-tertiary)",
              }}
            >
              <p style={{ fontSize: "2rem", marginBottom: "var(--space-sm)" }}>
                🔍
              </p>
              <p>
                No results found. Try different keywords or a broader search.
              </p>
            </div>
          )}

          {!searchLoading && results.length > 0 && (
            <div style={{ marginTop: "var(--space-xl)", maxWidth: 700 }}>
              <h2
                style={{
                  fontSize: "1.125rem",
                  fontWeight: 600,
                  marginBottom: "var(--space-md)",
                }}
              >
                Found {results.length} jobs
              </h2>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-md)",
                }}
              >
                {results.map((result, i) => (
                  <div
                    key={i}
                    className="glass-card"
                    style={{ padding: "var(--space-lg)" }}
                  >
                    {/* Header: source badge + title link + actions */}
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        gap: "var(--space-md)",
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "var(--space-sm)",
                            marginBottom: "var(--space-xs)",
                          }}
                        >
                          <span>
                            {SOURCE_ICONS[result.source] || "🌐"}
                          </span>
                          <span
                            className="badge badge-applied"
                            style={{ textTransform: "capitalize" }}
                          >
                            {result.source}
                          </span>
                        </div>
                        <h3
                          style={{
                            fontSize: "0.9375rem",
                            fontWeight: 600,
                            marginBottom: "var(--space-xs)",
                          }}
                        >
                          <a
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              color: "inherit",
                              textDecoration: "none",
                            }}
                            onMouseEnter={(e) =>
                              (e.currentTarget.style.textDecoration = "underline")
                            }
                            onMouseLeave={(e) =>
                              (e.currentTarget.style.textDecoration = "none")
                            }
                          >
                            {result.title}
                          </a>
                        </h3>
                        <p
                          style={{
                            fontSize: "0.8125rem",
                            color: "var(--text-secondary)",
                            lineHeight: 1.5,
                          }}
                        >
                          {result.snippet}
                        </p>
                      </div>

                      {/* Actions: Apply button + small link icon */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "var(--space-sm)",
                          flexShrink: 0,
                        }}
                      >
                        <a
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          title="Open job posting"
                          style={{
                            fontSize: "1.125rem",
                            lineHeight: 1,
                            opacity: 0.6,
                            transition: "opacity 0.15s",
                          }}
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.opacity = "1")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.opacity = "0.6")
                          }
                        >
                          🔗
                        </a>
                        <button
                          className="btn btn-primary"
                          onClick={() => handleApplyFromResult(result.url)}
                          style={{
                            fontSize: "0.8125rem",
                            padding: "0.375rem 0.875rem",
                          }}
                        >
                          🚀 Apply Now
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ──────── APPLY MODE ──────── */}
      {mode === "apply" && (
        <>
          {/* Job URL form */}
          <div
            className="glass-card"
            style={{ padding: "var(--space-xl)", maxWidth: 700 }}
          >
            <form onSubmit={handleRunAgent}>
              <div style={{ marginBottom: "var(--space-lg)" }}>
                <label className="input-label" htmlFor="job-url">
                  Job Posting URL
                </label>
                <input
                  id="job-url"
                  className="input"
                  type="url"
                  placeholder="https://linkedin.com/jobs/view/..."
                  value={jobUrl}
                  onChange={(e) => setJobUrl(e.target.value)}
                  required
                  disabled={running}
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
                disabled={running || !jobUrl.trim()}
                style={{ width: "100%" }}
              >
                {running
                  ? "⏳ Agents working..."
                  : "🚀 Run Multi-Agent Pipeline"}
              </button>
            </form>
          </div>

          {/* Error message */}
          {agentError && (
            <div
              className="error-msg"
              style={{ maxWidth: 700, marginTop: "var(--space-md)" }}
            >
              {agentError}
            </div>
          )}

          {/* Streaming progress */}
          {steps.length > 0 && (
            <div style={{ maxWidth: 700, marginTop: "var(--space-xl)" }}>
              <h2
                style={{
                  fontSize: "1.125rem",
                  fontWeight: 600,
                  marginBottom: "var(--space-md)",
                }}
              >
                {isComplete
                  ? "✅ Your application materials are ready for review"
                  : "⏳ Agent Progress"}
              </h2>

              <div className="stream-steps">
                {steps.map((step, i) => (
                  <div className="stream-step" key={i}>
                    {/* Step icon */}
                    <div
                      className={`step-icon ${
                        step.status === "done" ? "done" : "loading"
                      }`}
                    >
                      {STEP_ICONS[step.step] || "⚡"}
                    </div>

                    {/* Step details */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="step-label">{step.step}</div>
                      {step.preview && (
                        <div className="step-preview">{step.preview}</div>
                      )}
                      {step.message && (
                        <div
                          className="step-preview"
                          style={{ color: "var(--quality-low)" }}
                        >
                          {step.message}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Loading indicator when still running */}
                {running && (
                  <div className="stream-step">
                    <div className="step-icon loading">⏳</div>
                    <div style={{ flex: 1 }}>
                      <div
                        className="step-label"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        Waiting for next agent...
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Actions after completion */}
              {isComplete && (
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
                      setSteps([]);
                      setJobUrl("");
                      setAgentError("");
                    }}
                  >
                    🚀 Run Another
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
