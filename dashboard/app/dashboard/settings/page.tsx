"use client";

import { useState, useEffect, useRef } from "react";
import { getProfile, updateProfile, uploadResume } from "@/lib/api";
import { useToast } from "@/components/Toast";

/**
 * Settings Page — manage user profile, CV upload, and professional info.
 *
 * WHY a settings page?
 * The agent needs the user's name, email, phone, skills, and CV text
 * to generate personalized resumes and cover letters. Without this
 * page, users have to manually edit .env files.
 *
 * Sections:
 * 1. Profile — personal details (full_name, email, phone, links)
 * 2. Professional — background summary and skills tags
 * 3. Resume — PDF upload with extracted text preview
 */

interface UserProfile {
  full_name: string;
  email: string;
  background: string;
  skills: string[];
  cv_text: string;
  phone: string;
  linkedin_url: string;
  github_url: string;
}

const EMPTY_PROFILE: UserProfile = {
  full_name: "",
  email: "",
  background: "",
  skills: [],
  cv_text: "",
  phone: "",
  linkedin_url: "",
  github_url: "",
};

export default function SettingsPage() {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [profile, setProfile] = useState<UserProfile>(EMPTY_PROFILE);
  const [skillsInput, setSkillsInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showCvPreview, setShowCvPreview] = useState(false);

  // Load profile on mount
  useEffect(() => {
    const load = async () => {
      try {
        const data = await getProfile() as Record<string, unknown>;
        const p: UserProfile = {
          full_name: (data.full_name as string) || "",
          email: (data.email as string) || "",
          background: (data.background as string) || "",
          skills: Array.isArray(data.skills) ? (data.skills as string[]) : [],
          cv_text: (data.cv_text as string) || "",
          phone: (data.phone as string) || "",
          linkedin_url: (data.linkedin_url as string) || "",
          github_url: (data.github_url as string) || "",
        };
        setProfile(p);
        setSkillsInput(p.skills.join(", "));
      } catch {
        toast("Failed to load profile", "error");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /** Save profile to backend */
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    // Parse comma-separated skills into array
    const skills = skillsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      await updateProfile({
        full_name: profile.full_name,
        phone: profile.phone,
        linkedin_url: profile.linkedin_url,
        github_url: profile.github_url,
        background: profile.background,
        skills,
      });
      setProfile((prev) => ({ ...prev, skills }));
      toast("Profile saved!", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Save failed";
      toast(msg, "error");
    } finally {
      setSaving(false);
    }
  };

  /** Handle resume PDF upload */
  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      toast("Please upload a PDF file", "warning");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast("File too large (max 10 MB)", "warning");
      return;
    }

    setUploading(true);
    try {
      const result = await uploadResume(file);
      setProfile((prev) => ({ ...prev, cv_text: result.cv_text }));
      toast("Resume uploaded and parsed!", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      toast(msg, "error");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileUpload(file);
  };

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <h1>⚙️ Settings</h1>
        <p>Manage your profile, skills, and resume</p>
      </div>

      {loading ? (
        <div style={{ maxWidth: 640 }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="skeleton"
              style={{ height: 60, marginBottom: "var(--space-md)" }}
            />
          ))}
        </div>
      ) : (
        <form
          onSubmit={handleSave}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-xl)",
            maxWidth: 640,
          }}
        >
          {/* ──────── Profile Section ──────── */}
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

            <div
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
                  value={profile.full_name}
                  onChange={(e) =>
                    setProfile({ ...profile, full_name: e.target.value })
                  }
                />
              </div>

              <div>
                <label className="input-label" htmlFor="s-email">
                  Email
                </label>
                <input
                  id="s-email"
                  className="input"
                  type="email"
                  value={profile.email}
                  readOnly
                  style={{ opacity: 0.6, cursor: "not-allowed" }}
                />
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-tertiary)",
                    marginTop: "var(--space-xs)",
                  }}
                >
                  Email cannot be changed
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
          </div>

          {/* ──────── Professional Section ──────── */}
          <div className="glass-card" style={{ padding: "var(--space-xl)" }}>
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: 600,
                marginBottom: "var(--space-lg)",
              }}
            >
              💼 Professional
            </h2>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-md)",
              }}
            >
              <div>
                <label className="input-label" htmlFor="s-background">
                  Background Summary
                </label>
                <textarea
                  id="s-background"
                  className="input"
                  placeholder="e.g. 5 years full-stack developer specializing in React, Node.js, and cloud architecture..."
                  value={profile.background}
                  onChange={(e) =>
                    setProfile({ ...profile, background: e.target.value })
                  }
                  rows={4}
                  style={{ resize: "vertical" }}
                />
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-tertiary)",
                    marginTop: "var(--space-xs)",
                  }}
                >
                  Brief summary of your experience. The AI agent uses this to
                  tailor applications.
                </p>
              </div>

              <div>
                <label className="input-label" htmlFor="s-skills">
                  Skills{" "}
                  <span
                    style={{ color: "var(--text-tertiary)", fontWeight: 400 }}
                  >
                    (comma-separated)
                  </span>
                </label>
                <input
                  id="s-skills"
                  className="input"
                  type="text"
                  placeholder="Python, React, TypeScript, Docker, AWS..."
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                />
                {/* Skills preview tags */}
                {skillsInput.trim() && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 6,
                      marginTop: "var(--space-sm)",
                    }}
                  >
                    {skillsInput
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean)
                      .map((skill, i) => (
                        <span
                          key={i}
                          className="badge badge-applied"
                          style={{ fontSize: "0.75rem" }}
                        >
                          {skill}
                        </span>
                      ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ──────── Resume Section ──────── */}
          <div className="glass-card" style={{ padding: "var(--space-xl)" }}>
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: 600,
                marginBottom: "var(--space-lg)",
              }}
            >
              📄 Resume / CV
            </h2>

            <p
              style={{
                fontSize: "0.8125rem",
                color: "var(--text-secondary)",
                marginBottom: "var(--space-md)",
              }}
            >
              Upload your master resume (PDF). The AI agent reads the extracted
              text to tailor cover letters and bullets for each application.
            </p>

            {/* Upload drop zone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: "2px dashed rgba(255, 255, 255, 0.15)",
                borderRadius: 12,
                padding: "var(--space-xl) var(--space-lg)",
                textAlign: "center",
                cursor: uploading ? "wait" : "pointer",
                transition: "border-color 0.2s, background 0.2s",
                background: "rgba(255, 255, 255, 0.02)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLDivElement).style.borderColor =
                  "rgba(99, 102, 241, 0.5)";
                (e.currentTarget as HTMLDivElement).style.background =
                  "rgba(99, 102, 241, 0.05)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLDivElement).style.borderColor =
                  "rgba(255, 255, 255, 0.15)";
                (e.currentTarget as HTMLDivElement).style.background =
                  "rgba(255, 255, 255, 0.02)";
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                style={{ display: "none" }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileUpload(file);
                  e.target.value = "";
                }}
                disabled={uploading}
              />

              {uploading ? (
                <div>
                  <p style={{ fontSize: "2rem", marginBottom: "var(--space-sm)" }}>
                    ⏳
                  </p>
                  <p style={{ color: "var(--text-secondary)" }}>
                    Uploading and parsing resume...
                  </p>
                </div>
              ) : (
                <div>
                  <p style={{ fontSize: "2rem", marginBottom: "var(--space-sm)" }}>
                    📤
                  </p>
                  <p style={{ fontWeight: 500, marginBottom: "var(--space-xs)" }}>
                    Click to upload or drag and drop
                  </p>
                  <p
                    style={{
                      fontSize: "0.75rem",
                      color: "var(--text-tertiary)",
                    }}
                  >
                    PDF only · Max 10 MB
                  </p>
                </div>
              )}
            </div>

            {/* CV text preview */}
            {profile.cv_text && (
              <div style={{ marginTop: "var(--space-lg)" }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setShowCvPreview(!showCvPreview)}
                  style={{ fontSize: "0.8125rem", padding: "0.375rem 0.75rem" }}
                >
                  {showCvPreview ? "🔽 Hide CV Preview" : "▶️ Show CV Preview"}
                </button>

                {showCvPreview && (
                  <pre
                    style={{
                      marginTop: "var(--space-sm)",
                      padding: "var(--space-md)",
                      background: "rgba(0, 0, 0, 0.25)",
                      borderRadius: 8,
                      fontSize: "0.75rem",
                      lineHeight: 1.6,
                      color: "var(--text-secondary)",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      maxHeight: 300,
                      overflow: "auto",
                    }}
                  >
                    {profile.cv_text.slice(0, 500)}
                    {profile.cv_text.length > 500 && "\n\n... (truncated)"}
                  </pre>
                )}

                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-tertiary)",
                    marginTop: "var(--space-xs)",
                  }}
                >
                  ✅ Resume on file —{" "}
                  {profile.cv_text.length.toLocaleString()} characters extracted
                </p>
              </div>
            )}
          </div>

          {/* ──────── Save Button ──────── */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-md)",
            }}
          >
            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
              style={{ minWidth: 160 }}
            >
              {saving ? "Saving..." : "💾 Save Profile"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
