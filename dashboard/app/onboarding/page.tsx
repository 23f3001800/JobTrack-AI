"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  uploadResume,
  completeOnboarding,
  getCurrentUser,
  isLoggedIn,
  type ParsedProfile,
} from "@/lib/api";
import { useToast } from "@/components/Toast";

/**
 * Onboarding Wizard — 3-step flow for new users.
 *
 * Step 1: Upload resume (drag-and-drop PDF)
 * Step 2: Review & edit extracted profile data
 * Step 3: Confirm and start using the dashboard
 *
 * WHY a separate page outside /dashboard?
 * New users shouldn't see the sidebar or dashboard chrome before
 * their profile is set up. This gives a focused, guided experience.
 */

/** Empty profile template for manual setup */
function emptyProfile(): ParsedProfile {
  return {
    full_name: "",
    email: "",
    phone: "",
    linkedin_url: "",
    github_url: "",
    summary: "",
    skills: [],
    experience: [],
    education: [],
    projects: [],
    certifications: [],
    achievements: [],
  };
}

export default function OnboardingPage() {
  const router = useRouter();
  const { toast } = useToast();

  // ── Wizard state ──
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [profile, setProfile] = useState<ParsedProfile>(emptyProfile());
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // ── Collapsible sections in Step 2 ──
  const [projectsOpen, setProjectsOpen] = useState(false);
  const [certsOpen, setCertsOpen] = useState(false);

  // ── Editing indices for experience / education ──
  const [editingExp, setEditingExp] = useState<Set<number>>(new Set());
  const [editingEdu, setEditingEdu] = useState<Set<number>>(new Set());

  // ── Skills input ──
  const [skillInput, setSkillInput] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Redirect if not logged in
  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
    }
  }, [router]);

  // Pre-fill email from localStorage
  useEffect(() => {
    const user = getCurrentUser();
    if (user?.email) {
      setProfile((p) => ({ ...p, email: user.email }));
    }
  }, []);

  // ────────────────────────────────────────────
  // Step 1: Upload
  // ────────────────────────────────────────────

  const handleFile = useCallback(
    async (file: File) => {
      if (file.type !== "application/pdf") {
        toast("Please upload a PDF file", "error");
        return;
      }
      setUploading(true);
      try {
        const result = await uploadResume(file);
        if (result.parsed_profile) {
          // Pre-fill email from localStorage if not in parsed data
          const user = getCurrentUser();
          const merged: ParsedProfile = {
            ...emptyProfile(),
            ...result.parsed_profile,
            email: user?.email || result.parsed_profile.email || "",
          };
          setProfile(merged);
        }
        toast("Resume uploaded and parsed!", "success");
        setStep(2);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        toast(msg, "error");
      } finally {
        setUploading(false);
      }
    },
    [toast]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  // ────────────────────────────────────────────
  // Step 2: Profile helpers
  // ────────────────────────────────────────────

  const updateField = <K extends keyof ParsedProfile>(
    key: K,
    value: ParsedProfile[K]
  ) => {
    setProfile((p) => ({ ...p, [key]: value }));
  };

  const addSkill = () => {
    const trimmed = skillInput.trim();
    if (trimmed && !profile.skills.includes(trimmed)) {
      updateField("skills", [...profile.skills, trimmed]);
    }
    setSkillInput("");
  };

  const removeSkill = (skill: string) => {
    updateField(
      "skills",
      profile.skills.filter((s) => s !== skill)
    );
  };

  const addExperience = () => {
    const newExp = {
      title: "",
      company: "",
      start_date: "",
      end_date: "",
      bullets: [""],
    };
    const updated = [...profile.experience, newExp];
    updateField("experience", updated);
    setEditingExp((prev) => new Set(prev).add(updated.length - 1));
  };

  const updateExperience = (
    idx: number,
    field: string,
    value: string | string[]
  ) => {
    const updated = profile.experience.map((exp, i) =>
      i === idx ? { ...exp, [field]: value } : exp
    );
    updateField("experience", updated);
  };

  const removeExperience = (idx: number) => {
    updateField(
      "experience",
      profile.experience.filter((_, i) => i !== idx)
    );
    setEditingExp((prev) => {
      const next = new Set<number>();
      prev.forEach((v) => {
        if (v < idx) next.add(v);
        else if (v > idx) next.add(v - 1);
      });
      return next;
    });
  };

  const addEducation = () => {
    const newEdu = { degree: "", institution: "", year: "", details: "" };
    const updated = [...profile.education, newEdu];
    updateField("education", updated);
    setEditingEdu((prev) => new Set(prev).add(updated.length - 1));
  };

  const updateEducation = (idx: number, field: string, value: string) => {
    const updated = profile.education.map((edu, i) =>
      i === idx ? { ...edu, [field]: value } : edu
    );
    updateField("education", updated);
  };

  const removeEducation = (idx: number) => {
    updateField(
      "education",
      profile.education.filter((_, i) => i !== idx)
    );
    setEditingEdu((prev) => {
      const next = new Set<number>();
      prev.forEach((v) => {
        if (v < idx) next.add(v);
        else if (v > idx) next.add(v - 1);
      });
      return next;
    });
  };

  const addProject = () => {
    updateField("projects", [
      ...profile.projects,
      { name: "", description: "", technologies: [] },
    ]);
  };

  const updateProject = (
    idx: number,
    field: string,
    value: string | string[]
  ) => {
    const updated = profile.projects.map((proj, i) =>
      i === idx ? { ...proj, [field]: value } : proj
    );
    updateField("projects", updated);
  };

  const removeProject = (idx: number) => {
    updateField(
      "projects",
      profile.projects.filter((_, i) => i !== idx)
    );
  };

  // ────────────────────────────────────────────
  // Step 3: Complete onboarding
  // ────────────────────────────────────────────

  const handleComplete = async () => {
    setSaving(true);
    try {
      await completeOnboarding(profile as unknown as Record<string, unknown>);
      toast("Welcome aboard! 🎉", "success");
      router.push("/dashboard/search");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save profile";
      toast(msg, "error");
    } finally {
      setSaving(false);
    }
  };

  // ────────────────────────────────────────────
  // Progress Bar
  // ────────────────────────────────────────────

  const ProgressBar = () => {
    const steps = [
      { num: 1, label: "Upload" },
      { num: 2, label: "Review" },
      { num: 3, label: "Confirm" },
    ];
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0, marginBottom: "var(--space-2xl)" }}>
        {steps.map((s, i) => (
          <div key={s.num} style={{ display: "flex", alignItems: "center" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-sm)",
              }}
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  background:
                    step >= s.num
                      ? "var(--accent-gradient)"
                      : "var(--bg-input)",
                  color: step >= s.num ? "white" : "var(--text-tertiary)",
                  transition: "all var(--transition-base)",
                }}
              >
                {step > s.num ? "✓" : s.num}
              </div>
              <span
                style={{
                  fontSize: "0.8125rem",
                  fontWeight: 500,
                  color:
                    step >= s.num
                      ? "var(--text-primary)"
                      : "var(--text-tertiary)",
                }}
              >
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                style={{
                  width: 60,
                  height: 2,
                  margin: "0 var(--space-sm)",
                  background:
                    step > s.num
                      ? "var(--accent-start)"
                      : "var(--border-subtle)",
                  transition: "background var(--transition-base)",
                }}
              />
            )}
          </div>
        ))}
      </div>
    );
  };

  // ────────────────────────────────────────────
  // Render
  // ────────────────────────────────────────────

  return (
    <div className="login-container" style={{ alignItems: "flex-start", paddingTop: "var(--space-2xl)", paddingBottom: "var(--space-2xl)", overflowY: "auto" }}>
      <div style={{ width: "100%", maxWidth: 800, margin: "0 auto", padding: "0 var(--space-md)", position: "relative", zIndex: 1 }} className="animate-fade-in">
        <ProgressBar />

        {/* ═══════════════════════════════════════════
            STEP 1: Upload Resume
            ═══════════════════════════════════════════ */}
        {step === 1 && (
          <div style={{ textAlign: "center" }}>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "var(--space-xs)" }}>
              🎯 Welcome to AutoApply AI
            </h1>
            <p style={{ color: "var(--text-secondary)", marginBottom: "var(--space-2xl)", fontSize: "0.9375rem" }}>
              Upload your resume to get started. We&apos;ll extract your profile automatically.
            </p>

            {/* Drop zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className="glass-card"
              style={{
                padding: "var(--space-2xl) var(--space-xl)",
                border: dragOver
                  ? "2px dashed var(--accent-start)"
                  : "2px dashed var(--border-subtle)",
                borderRadius: "var(--radius-xl)",
                cursor: "pointer",
                transition: "all var(--transition-base)",
                background: dragOver
                  ? "rgba(99, 102, 241, 0.05)"
                  : "var(--bg-glass)",
                marginBottom: "var(--space-xl)",
              }}
            >
              {uploading ? (
                <div>
                  <div
                    style={{
                      fontSize: "2.5rem",
                      marginBottom: "var(--space-md)",
                      animation: "pulse 1.5s ease-in-out infinite",
                    }}
                  >
                    ⏳
                  </div>
                  <p style={{ fontWeight: 600, fontSize: "1rem" }}>
                    Uploading & parsing your resume...
                  </p>
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: "var(--space-xs)" }}>
                    This may take a few seconds
                  </p>
                  {/* Progress bar */}
                  <div
                    style={{
                      width: "60%",
                      height: 4,
                      background: "var(--bg-input)",
                      borderRadius: "var(--radius-full)",
                      margin: "var(--space-md) auto 0",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: "70%",
                        height: "100%",
                        background: "var(--accent-gradient)",
                        borderRadius: "var(--radius-full)",
                        animation: "shimmer 1.5s infinite",
                      }}
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: "2.5rem", marginBottom: "var(--space-md)" }}>
                    📄
                  </div>
                  <p style={{ fontWeight: 600, fontSize: "1rem" }}>
                    Drag &amp; drop your resume here
                  </p>
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: "var(--space-xs)" }}>
                    or click to browse — PDF only
                  </p>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                onChange={onFileChange}
                style={{ display: "none" }}
              />
            </div>

            {/* Skip button */}
            <button
              className="btn btn-ghost"
              onClick={() => {
                const user = getCurrentUser();
                setProfile({
                  ...emptyProfile(),
                  email: user?.email || "",
                });
                setStep(2);
              }}
              disabled={uploading}
              style={{ fontSize: "0.8125rem" }}
            >
              I&apos;ll set up my profile manually →
            </button>
          </div>
        )}

        {/* ═══════════════════════════════════════════
            STEP 2: Review & Edit Profile
            ═══════════════════════════════════════════ */}
        {step === 2 && (
          <div>
            <div style={{ textAlign: "center", marginBottom: "var(--space-xl)" }}>
              <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "var(--space-xs)" }}>
                📋 Review Your Profile
              </h1>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
                We extracted this from your resume. Review and edit anything that needs fixing.
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
              {/* ── Personal Info ── */}
              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--space-md)" }}>
                  👤 Personal Info
                </h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-md)" }}>
                  <div>
                    <label className="input-label">Full Name</label>
                    <input
                      className="input"
                      value={profile.full_name}
                      onChange={(e) => updateField("full_name", e.target.value)}
                      placeholder="John Doe"
                    />
                  </div>
                  <div>
                    <label className="input-label">Email</label>
                    <input
                      className="input"
                      value={profile.email}
                      readOnly
                      style={{ opacity: 0.6, cursor: "not-allowed" }}
                    />
                  </div>
                  <div>
                    <label className="input-label">Phone</label>
                    <input
                      className="input"
                      value={profile.phone}
                      onChange={(e) => updateField("phone", e.target.value)}
                      placeholder="+1 (555) 000-0000"
                    />
                  </div>
                  <div>
                    <label className="input-label">LinkedIn URL</label>
                    <input
                      className="input"
                      value={profile.linkedin_url}
                      onChange={(e) => updateField("linkedin_url", e.target.value)}
                      placeholder="https://linkedin.com/in/..."
                    />
                  </div>
                  <div style={{ gridColumn: "1 / -1" }}>
                    <label className="input-label">GitHub URL</label>
                    <input
                      className="input"
                      value={profile.github_url}
                      onChange={(e) => updateField("github_url", e.target.value)}
                      placeholder="https://github.com/..."
                    />
                  </div>
                </div>
              </div>

              {/* ── Professional Summary ── */}
              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--space-md)" }}>
                  📝 Professional Summary
                </h3>
                <textarea
                  className="input"
                  rows={4}
                  value={profile.summary}
                  onChange={(e) => updateField("summary", e.target.value)}
                  placeholder="Brief professional summary or background..."
                  style={{ resize: "vertical" }}
                />
              </div>

              {/* ── Skills ── */}
              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--space-md)" }}>
                  🛠️ Skills
                </h3>
                {/* Tags */}
                {profile.skills.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-xs)", marginBottom: "var(--space-md)" }}>
                    {profile.skills.map((skill) => (
                      <span
                        key={skill}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "4px 10px",
                          borderRadius: "var(--radius-full)",
                          background: "rgba(99, 102, 241, 0.15)",
                          color: "var(--accent-start)",
                          fontSize: "0.8125rem",
                          fontWeight: 500,
                        }}
                      >
                        {skill}
                        <button
                          onClick={() => removeSkill(skill)}
                          style={{
                            background: "none",
                            border: "none",
                            color: "var(--text-secondary)",
                            cursor: "pointer",
                            fontSize: "0.75rem",
                            padding: 0,
                            lineHeight: 1,
                          }}
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                {/* Input */}
                <div style={{ display: "flex", gap: "var(--space-sm)" }}>
                  <input
                    className="input"
                    value={skillInput}
                    onChange={(e) => setSkillInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === ",") {
                        e.preventDefault();
                        addSkill();
                      }
                    }}
                    placeholder="Type a skill and press Enter"
                    style={{ flex: 1 }}
                  />
                  <button className="btn btn-ghost" onClick={addSkill} type="button">
                    Add
                  </button>
                </div>
              </div>

              {/* ── Work Experience ── */}
              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--space-md)" }}>
                  💼 Work Experience
                </h3>
                {profile.experience.length === 0 && (
                  <p style={{ color: "var(--text-tertiary)", fontSize: "0.875rem", marginBottom: "var(--space-md)" }}>
                    No experience entries yet.
                  </p>
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
                  {profile.experience.map((exp, idx) => {
                    const isEditing = editingExp.has(idx);
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: "var(--space-md)",
                          background: "var(--bg-card)",
                          borderRadius: "var(--radius-md)",
                          border: "1px solid var(--border-subtle)",
                        }}
                      >
                        {isEditing ? (
                          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-sm)" }}>
                              <input
                                className="input"
                                value={exp.title}
                                onChange={(e) => updateExperience(idx, "title", e.target.value)}
                                placeholder="Job Title"
                              />
                              <input
                                className="input"
                                value={exp.company}
                                onChange={(e) => updateExperience(idx, "company", e.target.value)}
                                placeholder="Company"
                              />
                              <input
                                className="input"
                                value={exp.start_date}
                                onChange={(e) => updateExperience(idx, "start_date", e.target.value)}
                                placeholder="Start Date"
                              />
                              <input
                                className="input"
                                value={exp.end_date}
                                onChange={(e) => updateExperience(idx, "end_date", e.target.value)}
                                placeholder="End Date"
                              />
                            </div>
                            <div>
                              <label className="input-label">Bullet Points (one per line)</label>
                              <textarea
                                className="input"
                                rows={3}
                                value={exp.bullets.join("\n")}
                                onChange={(e) => updateExperience(idx, "bullets", e.target.value.split("\n"))}
                                placeholder="• Achievement or responsibility..."
                                style={{ resize: "vertical" }}
                              />
                            </div>
                            <div style={{ display: "flex", gap: "var(--space-sm)" }}>
                              <button
                                className="btn btn-ghost"
                                onClick={() => {
                                  setEditingExp((prev) => {
                                    const next = new Set(prev);
                                    next.delete(idx);
                                    return next;
                                  });
                                }}
                                style={{ fontSize: "0.8125rem" }}
                              >
                                Done
                              </button>
                              <button
                                className="btn btn-ghost"
                                onClick={() => removeExperience(idx)}
                                style={{ fontSize: "0.8125rem", color: "var(--quality-low)" }}
                              >
                                Remove
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div
                            style={{ cursor: "pointer" }}
                            onClick={() => setEditingExp((prev) => new Set(prev).add(idx))}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <p style={{ fontWeight: 600, fontSize: "0.9375rem" }}>
                                {exp.title || "Untitled"}{" "}
                                <span style={{ color: "var(--text-secondary)", fontWeight: 400 }}>
                                  @ {exp.company || "Company"}
                                </span>
                              </p>
                              <span style={{ fontSize: "0.75rem", color: "var(--text-link)" }}>Edit</span>
                            </div>
                            {(exp.start_date || exp.end_date) && (
                              <p style={{ fontSize: "0.8125rem", color: "var(--text-tertiary)", marginTop: 2 }}>
                                {exp.start_date} — {exp.end_date || "Present"}
                              </p>
                            )}
                            {exp.bullets.filter(Boolean).length > 0 && (
                              <ul style={{ marginTop: "var(--space-xs)", paddingLeft: "var(--space-md)" }}>
                                {exp.bullets.filter(Boolean).map((b, bi) => (
                                  <li key={bi} style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                                    {b}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <button
                  className="btn btn-ghost"
                  onClick={addExperience}
                  style={{ marginTop: "var(--space-md)", fontSize: "0.8125rem" }}
                >
                  + Add Experience
                </button>
              </div>

              {/* ── Education ── */}
              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--space-md)" }}>
                  🎓 Education
                </h3>
                {profile.education.length === 0 && (
                  <p style={{ color: "var(--text-tertiary)", fontSize: "0.875rem", marginBottom: "var(--space-md)" }}>
                    No education entries yet.
                  </p>
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
                  {profile.education.map((edu, idx) => {
                    const isEditing = editingEdu.has(idx);
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: "var(--space-md)",
                          background: "var(--bg-card)",
                          borderRadius: "var(--radius-md)",
                          border: "1px solid var(--border-subtle)",
                        }}
                      >
                        {isEditing ? (
                          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
                            <input
                              className="input"
                              value={edu.degree}
                              onChange={(e) => updateEducation(idx, "degree", e.target.value)}
                              placeholder="Degree (e.g., B.S. Computer Science)"
                            />
                            <input
                              className="input"
                              value={edu.institution}
                              onChange={(e) => updateEducation(idx, "institution", e.target.value)}
                              placeholder="Institution"
                            />
                            <input
                              className="input"
                              value={edu.year}
                              onChange={(e) => updateEducation(idx, "year", e.target.value)}
                              placeholder="Year (e.g., 2024)"
                            />
                            <textarea
                              className="input"
                              value={edu.details}
                              onChange={(e) => updateEducation(idx, "details", e.target.value)}
                              placeholder="Additional details (GPA, honors, etc.)"
                              rows={2}
                              style={{ resize: "vertical" }}
                            />
                            <div style={{ display: "flex", gap: "var(--space-sm)" }}>
                              <button
                                className="btn btn-ghost"
                                onClick={() => {
                                  setEditingEdu((prev) => {
                                    const next = new Set(prev);
                                    next.delete(idx);
                                    return next;
                                  });
                                }}
                                style={{ fontSize: "0.8125rem" }}
                              >
                                Done
                              </button>
                              <button
                                className="btn btn-ghost"
                                onClick={() => removeEducation(idx)}
                                style={{ fontSize: "0.8125rem", color: "var(--quality-low)" }}
                              >
                                Remove
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div
                            style={{ cursor: "pointer" }}
                            onClick={() => setEditingEdu((prev) => new Set(prev).add(idx))}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <p style={{ fontWeight: 600, fontSize: "0.9375rem" }}>
                                {edu.degree || "Degree"}
                              </p>
                              <span style={{ fontSize: "0.75rem", color: "var(--text-link)" }}>Edit</span>
                            </div>
                            <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                              {edu.institution || "Institution"}{edu.year ? ` · ${edu.year}` : ""}
                            </p>
                            {edu.details && (
                              <p style={{ fontSize: "0.8125rem", color: "var(--text-tertiary)", marginTop: 2 }}>
                                {edu.details}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <button
                  className="btn btn-ghost"
                  onClick={addEducation}
                  style={{ marginTop: "var(--space-md)", fontSize: "0.8125rem" }}
                >
                  + Add Education
                </button>
              </div>

              {/* ── Projects (collapsible) ── */}
              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                <button
                  onClick={() => setProjectsOpen(!projectsOpen)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-primary)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-sm)",
                    width: "100%",
                    fontSize: "1rem",
                    fontWeight: 600,
                    fontFamily: "inherit",
                    padding: 0,
                  }}
                >
                  <span style={{ transform: projectsOpen ? "rotate(90deg)" : "none", transition: "transform var(--transition-fast)", display: "inline-block" }}>
                    ▸
                  </span>
                  🚀 Projects ({profile.projects.length})
                </button>
                {projectsOpen && (
                  <div style={{ marginTop: "var(--space-md)" }}>
                    {profile.projects.length === 0 && (
                      <p style={{ color: "var(--text-tertiary)", fontSize: "0.875rem", marginBottom: "var(--space-md)" }}>
                        No projects yet.
                      </p>
                    )}
                    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
                      {profile.projects.map((proj, idx) => (
                        <div
                          key={idx}
                          style={{
                            padding: "var(--space-md)",
                            background: "var(--bg-card)",
                            borderRadius: "var(--radius-md)",
                            border: "1px solid var(--border-subtle)",
                          }}
                        >
                          <input
                            className="input"
                            value={proj.name}
                            onChange={(e) => updateProject(idx, "name", e.target.value)}
                            placeholder="Project Name"
                            style={{ marginBottom: "var(--space-sm)" }}
                          />
                          <textarea
                            className="input"
                            value={proj.description}
                            onChange={(e) => updateProject(idx, "description", e.target.value)}
                            placeholder="Description"
                            rows={2}
                            style={{ resize: "vertical", marginBottom: "var(--space-sm)" }}
                          />
                          <input
                            className="input"
                            value={proj.technologies.join(", ")}
                            onChange={(e) => updateProject(idx, "technologies", e.target.value.split(",").map((t) => t.trim()).filter(Boolean))}
                            placeholder="Technologies (comma-separated)"
                          />
                          <button
                            className="btn btn-ghost"
                            onClick={() => removeProject(idx)}
                            style={{ marginTop: "var(--space-sm)", fontSize: "0.8125rem", color: "var(--quality-low)" }}
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                    <button
                      className="btn btn-ghost"
                      onClick={addProject}
                      style={{ marginTop: "var(--space-md)", fontSize: "0.8125rem" }}
                    >
                      + Add Project
                    </button>
                  </div>
                )}
              </div>

              {/* ── Certifications & Achievements (collapsible) ── */}
              <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
                <button
                  onClick={() => setCertsOpen(!certsOpen)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-primary)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-sm)",
                    width: "100%",
                    fontSize: "1rem",
                    fontWeight: 600,
                    fontFamily: "inherit",
                    padding: 0,
                  }}
                >
                  <span style={{ transform: certsOpen ? "rotate(90deg)" : "none", transition: "transform var(--transition-fast)", display: "inline-block" }}>
                    ▸
                  </span>
                  🏆 Certifications &amp; Achievements
                </button>
                {certsOpen && (
                  <div style={{ marginTop: "var(--space-md)" }}>
                    <div style={{ marginBottom: "var(--space-md)" }}>
                      <label className="input-label">Certifications (one per line)</label>
                      <textarea
                        className="input"
                        rows={3}
                        value={profile.certifications.join("\n")}
                        onChange={(e) =>
                          updateField(
                            "certifications",
                            e.target.value.split("\n").filter((l) => l.trim())
                          )
                        }
                        placeholder="AWS Solutions Architect&#10;Google Cloud Professional..."
                        style={{ resize: "vertical" }}
                      />
                    </div>
                    <div>
                      <label className="input-label">Achievements (one per line)</label>
                      <textarea
                        className="input"
                        rows={3}
                        value={profile.achievements.join("\n")}
                        onChange={(e) =>
                          updateField(
                            "achievements",
                            e.target.value.split("\n").filter((l) => l.trim())
                          )
                        }
                        placeholder="Dean's List 2023&#10;Hackathon Winner..."
                        style={{ resize: "vertical" }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Navigation */}
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "var(--space-xl)" }}>
              <button className="btn btn-ghost" onClick={() => setStep(1)}>
                ← Back
              </button>
              <button className="btn btn-primary" onClick={() => setStep(3)}>
                Continue →
              </button>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════
            STEP 3: Confirmation
            ═══════════════════════════════════════════ */}
        {step === 3 && (
          <div style={{ textAlign: "center" }}>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "var(--space-xs)" }}>
              ✅ You&apos;re All Set!
            </h1>
            <p style={{ color: "var(--text-secondary)", marginBottom: "var(--space-xl)", fontSize: "0.9375rem" }}>
              Your profile is ready. Start exploring jobs.
            </p>

            {/* Summary card */}
            <div
              className="glass-card"
              style={{
                padding: "var(--space-xl)",
                maxWidth: 500,
                margin: "0 auto var(--space-xl)",
                textAlign: "left",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Name</span>
                  <span style={{ fontWeight: 600 }}>{profile.full_name || "—"}</span>
                </div>
                <div style={{ borderTop: "1px solid var(--border-subtle)" }} />
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Email</span>
                  <span style={{ fontWeight: 600 }}>{profile.email || "—"}</span>
                </div>
                <div style={{ borderTop: "1px solid var(--border-subtle)" }} />
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Skills</span>
                  <span style={{ fontWeight: 600 }}>{profile.skills.length} skills</span>
                </div>
                <div style={{ borderTop: "1px solid var(--border-subtle)" }} />
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Experience</span>
                  <span style={{ fontWeight: 600 }}>{profile.experience.length} entries</span>
                </div>
                <div style={{ borderTop: "1px solid var(--border-subtle)" }} />
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Education</span>
                  <span style={{ fontWeight: 600 }}>{profile.education.length} entries</span>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "center", gap: "var(--space-md)" }}>
              <button className="btn btn-ghost" onClick={() => setStep(2)}>
                ← Back to Edit
              </button>
              <button
                className="btn btn-primary"
                onClick={handleComplete}
                disabled={saving}
                style={{ padding: "0.75rem 2rem", fontSize: "1rem" }}
              >
                {saving ? "Saving..." : "🚀 Start Exploring Jobs"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
