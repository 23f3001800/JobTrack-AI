"use client";

import { useState } from "react";

/**
 * Job Search Page — discover jobs via web search.
 *
 * WHY a dedicated search page instead of just the URL input?
 * Users don't always have a job URL. This page lets them search
 * by keywords + location, see results as cards, and either:
 * 1. Run the agent directly on a result
 * 2. Save a job to their pipeline for later
 *
 * Uses POST /jobs/search which calls DuckDuckGo under the hood.
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

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [savedUrls, setSavedUrls] = useState<Set<string>>(new Set());

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setSearched(true);

    try {
      const token = localStorage.getItem("jt_access_token") || "";
      const res = await fetch(`${API_BASE}/jobs/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: query.trim(),
          location: location.trim(),
          max_results: 15,
        }),
      });

      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();
      setResults(data.results || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  /** Save a job to the user's pipeline */
  const handleSave = async (result: SearchResult) => {
    try {
      const token = localStorage.getItem("jt_access_token") || "";
      await fetch(`${API_BASE}/jobs/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          url: result.url,
          title: result.title,
          source: result.source,
        }),
      });
      setSavedUrls((prev) => new Set([...Array.from(prev), result.url]));
    } catch {
      // Silent fail
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <h1>🔍 Search Jobs</h1>
        <p>Discover job postings across the web</p>
      </div>

      {/* Search form */}
      <div
        className="glass-card"
        style={{ padding: "var(--space-xl)", maxWidth: 700 }}
      >
        <form
          onSubmit={handleSearch}
          style={{ display: "flex", gap: "var(--space-md)", flexWrap: "wrap" }}
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
              disabled={loading}
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
              disabled={loading}
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
              disabled={loading || !query.trim()}
            >
              {loading ? "Searching..." : "🔍 Search"}
            </button>
          </div>
        </form>
      </div>

      {/* Results */}
      {loading && (
        <div style={{ marginTop: "var(--space-xl)" }}>
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="skeleton"
              style={{ height: 100, marginBottom: "var(--space-md)", maxWidth: 700 }}
            />
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "var(--space-2xl)",
            color: "var(--text-tertiary)",
          }}
        >
          <p style={{ fontSize: "2rem", marginBottom: "var(--space-sm)" }}>🔍</p>
          <p>No results found. Try different keywords or a broader search.</p>
        </div>
      )}

      {!loading && results.length > 0 && (
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

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
            {results.map((result, i) => {
              const isSaved = savedUrls.has(result.url);
              return (
                <div
                  key={i}
                  className="glass-card"
                  style={{ padding: "var(--space-lg)" }}
                >
                  {/* Header: source icon + title */}
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
                        <span>{SOURCE_ICONS[result.source] || "🌐"}</span>
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
                        {result.title}
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

                    {/* Actions */}
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "var(--space-xs)",
                        flexShrink: 0,
                      }}
                    >
                      <a
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-ghost"
                        style={{ fontSize: "0.75rem", padding: "0.375rem 0.625rem" }}
                      >
                        🔗 View
                      </a>
                      <button
                        className={`btn ${isSaved ? "btn-ghost" : "btn-primary"}`}
                        onClick={() => handleSave(result)}
                        disabled={isSaved}
                        style={{ fontSize: "0.75rem", padding: "0.375rem 0.625rem" }}
                      >
                        {isSaved ? "✅ Saved" : "💾 Save"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
