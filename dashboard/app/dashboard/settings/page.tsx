"use client";

import { useState, useEffect } from "react";

/**
 * Settings Page — manage user profile, CV, and API settings.
 *
 * WHY a settings page?
 * The agent needs the user's name, email, phone, and CV path
 * to generate personalized resumes and cover letters. Without
 * this page, users have to manually edit .env files.
 *
 * Also provides a place to view API key, toggle dark mode, etc.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UserProfile {
  name: string;
  email: string;
  phone: string;
  cv_path: string;
  linkedin_url: string;
  github_url: string;
  default_location: string;
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile>({
    name: "",
    email: "",
    phone: "",
    cv_path: "",
    linkedin_url: "",
    github_url: "",
    default_location: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);

  // Load profile on mount
  useEffect(() => {
    const load = async () => {
      try {
        const token = localStorage.getItem("jt_access_token") || "";
        const res = await fetch(`${API_BASE}/auth/profile`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setProfile({
            name: data.name || "",
            email: data.email || "",
            phone: data.phone || "",
            cv_path: data.cv_path || "",
            linkedin_url: data.linkedin_url || "",
            github_url: data.github_url || "",
            default_location: data.default_location || "",
          });
        }
      } catch {
        // Will use empty defaults
      } finally {
        setLoading(false);
      }
    };
    load();

    // Load API key from localStorage
    const key = localStorage.getItem("jt_api_key");
    if (key) setApiKey(key);
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);

    try {
      const token = localStorage.getItem("jt_access_token") || "";
      const res = await fetch(`${API_BASE}/auth/profile`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(profile),
      });
      if (res.ok) {
        setSaved(true);
        // Auto-hide success message after 3 seconds
        setTimeout(() => setSaved(false), 3000);
      }
    } catch {
      // Silent fail
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("jt_access_token");
    localStorage.removeItem("jt_api_key");
    window.location.href = "/login";
  };

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <h1>⚙️ Settings</h1>
        <p>Manage your profile, CV, and preferences</p>
      </div>

      {loading ? (
        <div style={{ maxWidth: 600 }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="skeleton"
              style={{ height: 60, marginBottom: "var(--space-md)" }}
            />
          ))}
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-xl)",
            maxWidth: 600,
          }}
        >
          {/* Profile Section */}
          <div className="glass-card" style={{ padding: "var(--space-xl)" }}>
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: 600,
                marginBottom: "var(--space-lg)",
              }}
            >
              👤 Profile
            </h2>
            <form
              onSubmit={handleSave}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-md)",
              }}
            >
              <div>
                <label className="input-label" htmlFor="s-name">
                  Full Name
                </label>
                <input
                  id="s-name"
                  className="input"
                  type="text"
                  placeholder="Jane Doe"
                  value={profile.name}
                  onChange={(e) =>
                    setProfile({ ...profile, name: e.target.value })
                  }
                />
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "var(--space-md)",
                }}
              >
                <div>
                  <label className="input-label" htmlFor="s-email">
                    Email
                  </label>
                  <input
                    id="s-email"
                    className="input"
                    type="email"
                    placeholder="jane@example.com"
                    value={profile.email}
                    onChange={(e) =>
                      setProfile({ ...profile, email: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="input-label" htmlFor="s-phone">
                    Phone
                  </label>
                  <input
                    id="s-phone"
                    className="input"
                    type="tel"
                    placeholder="+1 555 123 4567"
                    value={profile.phone}
                    onChange={(e) =>
                      setProfile({ ...profile, phone: e.target.value })
                    }
                  />
                </div>
              </div>

              <div>
                <label className="input-label" htmlFor="s-cv">
                  CV File Path
                </label>
                <input
                  id="s-cv"
                  className="input"
                  type="text"
                  placeholder="/path/to/your/cv.pdf"
                  value={profile.cv_path}
                  onChange={(e) =>
                    setProfile({ ...profile, cv_path: e.target.value })
                  }
                />
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-tertiary)",
                    marginTop: "var(--space-xs)",
                  }}
                >
                  Path to your master CV (PDF). The agent reads this to tailor
                  bullets.
                </p>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "var(--space-md)",
                }}
              >
                <div>
                  <label className="input-label" htmlFor="s-linkedin">
                    LinkedIn URL
                  </label>
                  <input
                    id="s-linkedin"
                    className="input"
                    type="url"
                    placeholder="https://linkedin.com/in/janedoe"
                    value={profile.linkedin_url}
                    onChange={(e) =>
                      setProfile({ ...profile, linkedin_url: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="input-label" htmlFor="s-github">
                    GitHub URL
                  </label>
                  <input
                    id="s-github"
                    className="input"
                    type="url"
                    placeholder="https://github.com/janedoe"
                    value={profile.github_url}
                    onChange={(e) =>
                      setProfile({ ...profile, github_url: e.target.value })
                    }
                  />
                </div>
              </div>

              <div>
                <label className="input-label" htmlFor="s-location">
                  Default Job Location
                </label>
                <input
                  id="s-location"
                  className="input"
                  type="text"
                  placeholder="Remote, London, San Francisco..."
                  value={profile.default_location}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      default_location: e.target.value,
                    })
                  }
                />
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-md)",
                  marginTop: "var(--space-sm)",
                }}
              >
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving}
                >
                  {saving ? "Saving..." : "💾 Save Profile"}
                </button>
                {saved && (
                  <span
                    style={{
                      color: "var(--success)",
                      fontSize: "0.875rem",
                      fontWeight: 500,
                    }}
                  >
                    ✅ Profile saved!
                  </span>
                )}
              </div>
            </form>
          </div>

          {/* API Key Section */}
          <div className="glass-card" style={{ padding: "var(--space-xl)" }}>
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: 600,
                marginBottom: "var(--space-lg)",
              }}
            >
              🔑 API Key
            </h2>
            <p
              style={{
                fontSize: "0.8125rem",
                color: "var(--text-secondary)",
                marginBottom: "var(--space-md)",
              }}
            >
              Use this key for CLI or MCP access. Keep it secret.
            </p>
            <div
              style={{
                display: "flex",
                gap: "var(--space-sm)",
                alignItems: "center",
              }}
            >
              <input
                className="input"
                type={showKey ? "text" : "password"}
                value={apiKey || "No API key stored"}
                readOnly
                style={{ flex: 1, fontFamily: "monospace", fontSize: "0.8125rem" }}
              />
              <button
                className="btn btn-ghost"
                onClick={() => setShowKey(!showKey)}
                style={{ fontSize: "0.75rem" }}
              >
                {showKey ? "🙈 Hide" : "👁️ Show"}
              </button>
            </div>
          </div>

          {/* Danger Zone */}
          <div
            className="glass-card"
            style={{
              padding: "var(--space-xl)",
              borderColor: "rgba(239, 68, 68, 0.3)",
            }}
          >
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: 600,
                marginBottom: "var(--space-md)",
                color: "var(--error)",
              }}
            >
              ⚠️ Danger Zone
            </h2>
            <button
              className="btn"
              onClick={handleLogout}
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                color: "var(--error)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
              }}
            >
              🚪 Log Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
