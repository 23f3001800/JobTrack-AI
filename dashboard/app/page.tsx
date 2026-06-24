/**
 * Landing Page — the public-facing homepage for JobTrack AI.
 *
 * WHY a dedicated landing page instead of redirecting to /login?
 * First impressions matter. A polished landing page with feature
 * showcase, architecture diagram, and CTA gives credibility before
 * asking users to sign up.
 */

import Link from "next/link";

export default function HomePage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "linear-gradient(135deg, var(--bg-primary) 0%, #0a0a1a 50%, #0d1117 100%)",
        color: "var(--text-primary)",
        overflow: "hidden",
      }}
    >
      {/* ── Navigation ── */}
      <nav
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "var(--space-lg) var(--space-2xl)",
          maxWidth: 1200,
          margin: "0 auto",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-sm)" }}>
          <span style={{ fontSize: "1.5rem" }}>🎯</span>
          <span style={{ fontSize: "1.25rem", fontWeight: 700 }}>JobTrack AI</span>
        </div>
        <div style={{ display: "flex", gap: "var(--space-md)" }}>
          <Link
            href="/login"
            className="btn btn-ghost"
            style={{ fontSize: "0.875rem" }}
          >
            Log In
          </Link>
          <Link
            href="/login"
            className="btn btn-primary"
            style={{ fontSize: "0.875rem" }}
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* ── Hero Section ── */}
      <section
        style={{
          textAlign: "center",
          padding: "80px var(--space-2xl) 60px",
          maxWidth: 900,
          margin: "0 auto",
          position: "relative",
        }}
      >
        {/* Glow effect */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: 600,
            height: 600,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />

        <div
          style={{
            display: "inline-block",
            padding: "var(--space-xs) var(--space-md)",
            borderRadius: 20,
            background: "rgba(99, 102, 241, 0.15)",
            border: "1px solid rgba(99, 102, 241, 0.3)",
            fontSize: "0.8125rem",
            color: "var(--accent)",
            marginBottom: "var(--space-lg)",
            fontWeight: 500,
          }}
        >
          ✨ Powered by 5 AI Agents
        </div>

        <h1
          style={{
            fontSize: "clamp(2.5rem, 6vw, 4rem)",
            fontWeight: 800,
            lineHeight: 1.1,
            marginBottom: "var(--space-lg)",
            letterSpacing: "-0.03em",
          }}
        >
          Job applications{" "}
          <span
            style={{
              background: "linear-gradient(135deg, var(--accent), #818cf8, #c084fc)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            that don&apos;t suck
          </span>
        </h1>

        <p
          style={{
            fontSize: "1.25rem",
            color: "var(--text-secondary)",
            maxWidth: 650,
            margin: "0 auto var(--space-xl)",
            lineHeight: 1.6,
          }}
        >
          A multi-agent AI pipeline that researches companies, tailors your CV,
          writes personalised cover letters, and quality-checks everything —
          in under 8 minutes.
        </p>

        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: "var(--space-md)",
            marginBottom: "var(--space-2xl)",
          }}
        >
          <Link
            href="/login"
            className="btn btn-primary"
            style={{
              fontSize: "1rem",
              padding: "var(--space-md) var(--space-xl)",
            }}
          >
            🚀 Start Applying
          </Link>
          <a
            href="https://github.com/you/jobtrack-ai"
            className="btn btn-ghost"
            style={{
              fontSize: "1rem",
              padding: "var(--space-md) var(--space-xl)",
            }}
            target="_blank"
            rel="noopener noreferrer"
          >
            ⭐ GitHub
          </a>
        </div>
      </section>

      {/* ── Stats Bar ── */}
      <section
        style={{
          display: "flex",
          justifyContent: "center",
          gap: "var(--space-2xl)",
          padding: "var(--space-xl) var(--space-2xl)",
          flexWrap: "wrap",
        }}
      >
        {[
          { value: "5", label: "AI Agents" },
          { value: "< 8min", label: "Per Application" },
          { value: "4.2/5", label: "Quality Score" },
          { value: "17", label: "API Endpoints" },
        ].map((stat) => (
          <div key={stat.label} style={{ textAlign: "center" }}>
            <div
              style={{
                fontSize: "1.75rem",
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              {stat.value}
            </div>
            <div
              style={{
                fontSize: "0.8125rem",
                color: "var(--text-tertiary)",
                marginTop: "var(--space-xs)",
              }}
            >
              {stat.label}
            </div>
          </div>
        ))}
      </section>

      {/* ── Pipeline Section ── */}
      <section
        style={{
          maxWidth: 1000,
          margin: "0 auto",
          padding: "60px var(--space-2xl)",
        }}
      >
        <h2
          style={{
            textAlign: "center",
            fontSize: "2rem",
            fontWeight: 700,
            marginBottom: "var(--space-sm)",
          }}
        >
          How it works
        </h2>
        <p
          style={{
            textAlign: "center",
            color: "var(--text-secondary)",
            marginBottom: "var(--space-2xl)",
            fontSize: "1rem",
          }}
        >
          Five specialized agents collaborate to build your perfect application
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))",
            gap: "var(--space-md)",
          }}
        >
          {[
            {
              icon: "🔍",
              name: "Scout",
              desc: "Scrapes job postings & searches the web for opportunities",
              step: 1,
            },
            {
              icon: "🏢",
              name: "Research",
              desc: "Deep-dives into the company, culture, and role fit",
              step: 2,
            },
            {
              icon: "✍️",
              name: "Writer",
              desc: "Tailors your CV, writes cover letters & LinkedIn DMs",
              step: 3,
            },
            {
              icon: "⭐",
              name: "Quality",
              desc: "LLM-as-judge scoring with automatic rewrite loop",
              step: 4,
            },
            {
              icon: "📤",
              name: "Applier",
              desc: "Logs to tracker, generates ATS-friendly PDF resumes",
              step: 5,
            },
          ].map((agent) => (
            <div
              key={agent.name}
              className="glass-card"
              style={{
                padding: "var(--space-lg)",
                textAlign: "center",
                position: "relative",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 8,
                  right: 12,
                  fontSize: "0.6875rem",
                  color: "var(--text-tertiary)",
                  fontWeight: 600,
                }}
              >
                STEP {agent.step}
              </div>
              <div style={{ fontSize: "2rem", marginBottom: "var(--space-sm)" }}>
                {agent.icon}
              </div>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: "0.9375rem",
                  marginBottom: "var(--space-xs)",
                }}
              >
                {agent.name}
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.4,
                }}
              >
                {agent.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features Grid ── */}
      <section
        style={{
          maxWidth: 1000,
          margin: "0 auto",
          padding: "40px var(--space-2xl) 80px",
        }}
      >
        <h2
          style={{
            textAlign: "center",
            fontSize: "2rem",
            fontWeight: 700,
            marginBottom: "var(--space-2xl)",
          }}
        >
          Everything you need
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: "var(--space-lg)",
          }}
        >
          {[
            {
              icon: "📊",
              title: "Real-time Dashboard",
              desc: "Track all applications with live status updates, quality scores, and response rate analytics.",
            },
            {
              icon: "📄",
              title: "PDF Resume Generator",
              desc: "ATS-friendly tailored resumes generated per job with professional formatting.",
            },
            {
              icon: "🔍",
              title: "Job Discovery",
              desc: "Search across LinkedIn, Indeed, Greenhouse, and Lever without leaving the app.",
            },
            {
              icon: "🎤",
              title: "Interview Prep",
              desc: "Auto-generated technical, behavioral, and company-specific interview questions.",
            },
            {
              icon: "📬",
              title: "Follow-up Generator",
              desc: "Context-aware follow-up messages for email and LinkedIn that actually get replies.",
            },
            {
              icon: "🔐",
              title: "Secure & Private",
              desc: "JWT authentication, API key access, row-level security. Your data stays yours.",
            },
          ].map((feat) => (
            <div
              key={feat.title}
              className="glass-card"
              style={{ padding: "var(--space-xl)" }}
            >
              <div style={{ fontSize: "1.5rem", marginBottom: "var(--space-sm)" }}>
                {feat.icon}
              </div>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: "1rem",
                  marginBottom: "var(--space-xs)",
                }}
              >
                {feat.title}
              </div>
              <div
                style={{
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.5,
                }}
              >
                {feat.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ── */}
      <footer
        style={{
          textAlign: "center",
          padding: "var(--space-xl) var(--space-2xl)",
          borderTop: "1px solid var(--border)",
          color: "var(--text-tertiary)",
          fontSize: "0.8125rem",
        }}
      >
        Built with LangGraph, Claude, Next.js, FastAPI, and Supabase.
        <br />
        © {new Date().getFullYear()} JobTrack AI
      </footer>
    </div>
  );
}
