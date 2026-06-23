"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { runAgent, type StreamStep } from "@/lib/api";

/**
 * New Application Page — job URL input + real-time streaming progress.
 *
 * WHY a dedicated page instead of a modal?
 * The agent pipeline takes 30-60 seconds. A modal would block the UI.
 * A full page gives room for the streaming progress display and
 * lets the user see the generated materials as they arrive.
 *
 * The streaming display shows each agent's completion in real-time:
 * Scout → Research → Writer → Quality → Apply
 */

/** Map step names to emoji icons for visual progress */
const STEP_ICONS: Record<string, string> = {
  "Job analysis": "🔍",
  "Company research": "🏢",
  "Role fit analysis": "🎯",
  "CV tailoring": "📝",
  "Cover letter": "✉️",
  "LinkedIn DM": "💬",
  "Application logged": "✅",
  complete: "🎉",
  error: "❌",
};

export default function NewApplicationPage() {
  const router = useRouter();
  const [jobUrl, setJobUrl] = useState("");
  const [background, setBackground] = useState("");
  const [steps, setSteps] = useState<StreamStep[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobUrl.trim()) return;

    setError("");
    setSteps([]);
    setRunning(true);

    try {
      await runAgent(
        jobUrl.trim(),
        background.trim() || "Software developer",
        (step) => {
          // Append each streaming step to the list
          setSteps((prev) => [...prev, step]);
        }
      );
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Pipeline failed";
      setError(message);
    } finally {
      setRunning(false);
    }
  };

  const isComplete = steps.some((s) => s.step === "complete");

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <h1>🚀 New Application</h1>
        <p>Paste a job URL and let the AI agents do the work</p>
      </div>

      {/* Job URL form */}
      <div
        className="glass-card"
        style={{ padding: "var(--space-xl)", maxWidth: 700 }}
      >
        <form onSubmit={handleRun}>
          <div style={{ marginBottom: "var(--space-md)" }}>
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
          </div>

          <div style={{ marginBottom: "var(--space-lg)" }}>
            <label className="input-label" htmlFor="background">
              Your Background{" "}
              <span style={{ color: "var(--text-tertiary)", fontWeight: 400 }}>
                (optional — uses your profile if empty)
              </span>
            </label>
            <textarea
              id="background"
              className="input"
              placeholder="e.g. 3 years Python developer, built RAG systems, experience with FastAPI and Docker..."
              value={background}
              onChange={(e) => setBackground(e.target.value)}
              rows={3}
              style={{ resize: "vertical" }}
              disabled={running}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={running || !jobUrl.trim()}
            style={{ width: "100%" }}
          >
            {running ? "⏳ Agents working..." : "🚀 Run Multi-Agent Pipeline"}
          </button>
        </form>
      </div>

      {/* Error message */}
      {error && (
        <div
          className="error-msg"
          style={{ maxWidth: 700, marginTop: "var(--space-md)" }}
        >
          {error}
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
            {isComplete ? "✅ Pipeline Complete" : "⏳ Agent Progress"}
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
                  <div className="step-label" style={{ color: "var(--text-secondary)" }}>
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
                onClick={() => router.push("/dashboard/tracker")}
              >
                📋 View in Tracker
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => {
                  setSteps([]);
                  setJobUrl("");
                  setBackground("");
                }}
              >
                🚀 Run Another
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
