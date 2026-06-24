/**
 * API Client — typed fetch wrapper for the JobTrack AI backend.
 *
 * WHY a custom client instead of using fetch directly?
 * 1. Centralized auth header injection (JWT or API key)
 * 2. Typed responses for every endpoint
 * 3. NDJSON streaming support for the /run endpoint
 * 4. Consistent error handling across all pages
 *
 * The base URL comes from NEXT_PUBLIC_API_URL env var.
 * In development, this points to http://localhost:8000.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────

/** Application data returned by /tracker */
export interface Application {
  id?: string;
  company: string;
  job_title: string;
  status: string;
  applied_at?: string;
  cover_letter?: string;
  tailored_bullets?: string;
  outreach_dm?: string;
  quality_score?: number;
  role_fit?: string;
  job_analysis?: string;
  company_profile?: string;
  notes?: string;
}

/** Streaming step from /run endpoint */
export interface StreamStep {
  step: string;
  status: string;
  preview?: string;
  message?: string;
  thread_id?: string;
}

/** Dashboard stats from /admin/stats */
export interface DashboardStats {
  total_applications: number;
  by_status: Record<string, number>;
  average_quality_score: number;
  quality_rated_count: number;
}

/** Login response */
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: { id: string; email: string; role?: string };
}

// ──────────────────────────────────────────────
// Auth token management
// ──────────────────────────────────────────────

/**
 * Get the auth token from localStorage.
 *
 * WHY localStorage instead of cookies?
 * Supabase JS client stores tokens in localStorage by default.
 * Using the same storage keeps things consistent. For production,
 * consider httpOnly cookies for better XSS protection.
 */
function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("jt_access_token") || "";
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem("jt_access_token", access);
  localStorage.setItem("jt_refresh_token", refresh);
}

export function clearTokens(): void {
  localStorage.removeItem("jt_access_token");
  localStorage.removeItem("jt_refresh_token");
  localStorage.removeItem("jt_user");
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

/** Get the current user object from localStorage */
export function getCurrentUser(): { id: string; email: string; role?: string } | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("jt_user");
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

/** Get the current user's role (defaults to 'user') */
export function getUserRole(): string {
  return getCurrentUser()?.role || "user";
}

// ──────────────────────────────────────────────
// Core fetch wrapper
// ──────────────────────────────────────────────

/**
 * Authenticated fetch — injects Bearer token and handles errors.
 *
 * WHY not use axios?
 * fetch is built-in, supports streaming (ReadableStream), and is
 * lighter weight. We only need basic request/response handling.
 */
async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// ──────────────────────────────────────────────
// API methods
// ──────────────────────────────────────────────

/** POST /auth/login — authenticate and store tokens */
export async function login(email: string, password: string): Promise<LoginResponse> {
  const data = await apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setTokens(data.access_token, data.refresh_token);
  // Store user data for role-based UI rendering
  if (data.user) {
    localStorage.setItem("jt_user", JSON.stringify(data.user));
  }
  return data;
}

/** POST /auth/signup — create account */
export async function signup(email: string, password: string) {
  return apiFetch<{ user_id: string; email: string; message: string }>(
    "/auth/signup",
    { method: "POST", body: JSON.stringify({ email, password }) }
  );
}

/** GET /tracker — fetch user's applications */
export async function getApplications(): Promise<{
  applications: Application[];
  total: number;
}> {
  return apiFetch("/tracker");
}

/** PATCH /tracker/{id}/status — update application status */
export async function updateStatus(appId: string, status: string) {
  return apiFetch(`/tracker/${appId}/status?status=${status}`, {
    method: "PATCH",
  });
}

/** DELETE /tracker/{id} — remove application */
export async function deleteApplication(appId: string) {
  return apiFetch(`/tracker/${appId}`, { method: "DELETE" });
}

/** PATCH /tracker/{id}/notes — update application notes */
export async function updateNotes(appId: string, notes: string) {
  return apiFetch(`/tracker/${appId}/notes`, {
    method: "PATCH",
    body: JSON.stringify({ notes }),
  });
}

/** GET /admin/stats — dashboard statistics */
export async function getStats(): Promise<DashboardStats> {
  return apiFetch("/admin/stats");
}

/** GET /auth/profile — get user profile */
export async function getProfile() {
  return apiFetch("/auth/profile");
}

/**
 * POST /run — execute the multi-agent pipeline with streaming.
 *
 * WHY a callback-based API instead of returning a promise?
 * The /run endpoint returns NDJSON (one JSON object per line).
 * Each line is a step update. We stream these to the UI in real-time
 * using a ReadableStream reader, calling onStep for each line.
 *
 * This gives the user visual progress as each agent completes:
 * "Scraping job..." → "Researching company..." → "Writing cover letter..."
 */
export async function runAgent(
  jobUrl: string,
  userBackground: string,
  onStep: (step: StreamStep) => void
): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ job_url: jobUrl, user_background: userBackground }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  // Read NDJSON stream line by line
  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");

    // Process all complete lines, keep the last partial line in buffer
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.trim()) {
        try {
          const step: StreamStep = JSON.parse(line);
          onStep(step);
        } catch {
          // Skip malformed lines
        }
      }
    }
  }
}

/** POST /jobs/search — search for job postings */
export async function searchJobs(query: string, location: string = "", maxResults: number = 10) {
  return apiFetch<{ query: string; location: string; results: Array<{ title: string; url: string; snippet: string; source: string }>; total: number }>(
    "/jobs/search",
    { method: "POST", body: JSON.stringify({ query, location, max_results: maxResults }) }
  );
}

/** POST /jobs/save — save a job to pipeline */
export async function saveJob(url: string, title: string, company: string = "", source: string = "") {
  return apiFetch("/jobs/save", {
    method: "POST",
    body: JSON.stringify({ url, title, company, source }),
  });
}

/** POST /auth/profile/resume — upload resume PDF */
export async function uploadResume(file: File): Promise<{ message: string; cv_text: string }> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/auth/profile/resume`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Upload failed: ${res.status}`);
  }

  return res.json();
}

/** PATCH /auth/profile — update user profile */
export async function updateProfile(data: Record<string, unknown>) {
  return apiFetch("/auth/profile", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
