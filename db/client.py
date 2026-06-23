"""Database client — dual-backend (Supabase or JSON fallback).

WHY two backends?
- Supabase: Used in production and when SUPABASE_URL is configured.
  Provides PostgreSQL, auth, realtime, and storage.
- JSON fallback: Used in local development and CI tests when no
  Supabase credentials are available. Stores data in ./workspace/
  just like the original implementation.

The rest of the application calls get_db() and gets a client object
with the same interface regardless of which backend is active.

Usage:
    from db import get_db
    db = get_db()
    db.log_application({...})
    apps = db.get_applications()
"""
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# ──────────────────────────────────────────────
# Supabase Backend
# ──────────────────────────────────────────────

class SupabaseDB:
    """Production database client using Supabase PostgreSQL.

    WHY a class instead of module-level functions?
    Encapsulates the Supabase client connection and makes it easy
    to inject a mock client in tests. Also allows future connection
    pooling and retry logic in one place.
    """

    def __init__(self):
        """Initialize Supabase client from environment variables.

        SUPABASE_URL: Your project's API URL (from Supabase dashboard)
        SUPABASE_SERVICE_KEY: Service role key (bypasses RLS for server-side ops)

        WHY service key instead of anon key?
        The backend API runs server-side and needs to write data for any user.
        The anon key would be restricted by RLS to the currently-authenticated user,
        which doesn't work for server-side agent operations. The frontend uses
        the anon key with user JWTs.
        """
        from supabase import create_client
        self.client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"]
        )

    def log_application(self, data: dict, user_id: str = None) -> dict:
        """Insert a new application into the applications table.

        Args:
            data: Application data (company, job_title, cover_letter, etc.)
            user_id: The user who owns this application. None for legacy/anon.

        Returns:
            The inserted row as a dict.
        """
        row = {
            "company": data.get("company", ""),
            "job_title": data.get("job_title", ""),
            "cover_letter": data.get("cover_letter", ""),
            "tailored_bullets": data.get("tailored_bullets", ""),
            "outreach_dm": data.get("outreach_dm", ""),
            "job_analysis": data.get("job_analysis", ""),
            "company_profile": data.get("company_profile", ""),
            "role_fit": data.get("role_fit", ""),
            "quality_score": data.get("quality_score", 0),
            "status": data.get("status", "applied"),
        }
        # Only include user_id if provided (skip for legacy single-user mode)
        if user_id:
            row["user_id"] = user_id

        result = self.client.table("applications").insert(row).execute()
        return result.data[0] if result.data else row

    def get_applications(self, user_id: str = None) -> list:
        """Fetch all applications, optionally filtered by user.

        Args:
            user_id: If provided, only return this user's applications.
                     If None, return all (admin use case).

        Returns:
            List of application dicts, ordered by applied_at descending.
        """
        query = self.client.table("applications").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        result = query.order("applied_at", desc=True).execute()
        return result.data or []

    def update_application_status(self, app_id: str, status: str) -> dict:
        """Update an application's status (for Kanban board drag-and-drop).

        Args:
            app_id: UUID of the application to update.
            status: New status value (must match application_status enum).

        Returns:
            The updated row.
        """
        result = (
            self.client.table("applications")
            .update({"status": status})
            .eq("id", app_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_profile(self, user_id: str) -> dict:
        """Fetch a user's profile.

        Returns:
            Profile dict or empty dict if not found.
        """
        result = (
            self.client.table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return result.data or {}

    def update_profile(self, user_id: str, data: dict) -> dict:
        """Update a user's profile fields.

        Args:
            user_id: UUID of the user.
            data: Dict of fields to update (background, skills, cv_text, etc.)

        Returns:
            The updated profile row.
        """
        result = (
            self.client.table("profiles")
            .update(data)
            .eq("id", user_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def save_job(self, data: dict, user_id: str = None) -> dict:
        """Save a scraped job posting to the jobs table.

        WHY save jobs separately from applications?
        A user might discover a job via search but not apply immediately.
        Jobs are the "pipeline" — applications are the "completed" ones.
        """
        row = {
            "url": data.get("url", ""),
            "title": data.get("title", ""),
            "company": data.get("company", ""),
            "location": data.get("location", ""),
            "salary": data.get("salary", ""),
            "requirements": data.get("requirements", ""),
            "raw_analysis": data.get("raw_analysis", ""),
            "source": data.get("source", "manual"),
        }
        if user_id:
            row["user_id"] = user_id

        result = self.client.table("jobs").insert(row).execute()
        return result.data[0] if result.data else row


# ──────────────────────────────────────────────
# JSON File Fallback
# ──────────────────────────────────────────────

class JsonDB:
    """Local JSON file storage — zero-dependency fallback.

    WHY keep this? Three reasons:
    1. Local development without Supabase credentials
    2. CI tests don't need a database connection
    3. Backwards compatibility with existing workspace/ files

    Data is stored in WORKSPACE_DIR (default: ./workspace/):
    - tracker.json — array of application entries
    - {company}_cover_letter.txt — cover letter files
    - {company}_tailored_bullets.txt — bullet point files
    """

    def __init__(self):
        self.workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.tracker_path = self.workspace / "tracker.json"

    def _load_tracker(self) -> list:
        """Load tracker.json, returning empty list if missing."""
        if self.tracker_path.exists():
            return json.loads(self.tracker_path.read_text())
        return []

    def _save_tracker(self, data: list) -> None:
        """Write tracker data back to JSON file."""
        self.tracker_path.write_text(json.dumps(data, indent=2))

    def log_application(self, data: dict, user_id: str = None) -> dict:
        """Append an application to tracker.json and save output files.

        Mirrors the original _log_application() behavior from executor.py.
        """
        slug = data.get("company", "unknown").lower().replace(" ", "_")

        # Save cover letter and bullets as separate text files
        # WHY separate files? Easy to copy-paste into actual applications,
        # and the MCP server can serve them individually to Claude Desktop.
        cover_letter = data.get("cover_letter", "")
        if cover_letter:
            (self.workspace / f"{slug}_cover_letter.txt").write_text(cover_letter)

        tailored_bullets = data.get("tailored_bullets", "")
        if tailored_bullets:
            (self.workspace / f"{slug}_tailored_bullets.txt").write_text(tailored_bullets)

        # Build tracker entry
        entry = {
            "company": data.get("company", ""),
            "job_title": data.get("job_title", ""),
            "applied_at": datetime.now().isoformat(),
            "status": data.get("status", "applied"),
            "job_analysis": data.get("job_analysis", ""),
            "company_profile": data.get("company_profile", ""),
            "tailored_bullets": tailored_bullets,
            "role_fit": data.get("role_fit", ""),
            "quality_score": data.get("quality_score", 0),
        }

        # Append to tracker
        tracker = self._load_tracker()
        tracker.append(entry)
        self._save_tracker(tracker)

        return entry

    def get_applications(self, user_id: str = None) -> list:
        """Return all applications from tracker.json.

        user_id is ignored in JSON mode (single-user).
        """
        return self._load_tracker()

    def update_application_status(self, app_id: str, status: str) -> dict:
        """Update status by index (JSON mode doesn't have UUIDs).

        In JSON mode, app_id is treated as the list index.
        """
        tracker = self._load_tracker()
        try:
            idx = int(app_id)
            if 0 <= idx < len(tracker):
                tracker[idx]["status"] = status
                self._save_tracker(tracker)
                return tracker[idx]
        except (ValueError, IndexError):
            pass
        return {}

    def get_profile(self, user_id: str = None) -> dict:
        """Return a stub profile in JSON mode."""
        return {
            "full_name": "Local User",
            "background": os.getenv("USER_BACKGROUND", ""),
            "skills": [],
            "cv_text": "",
        }

    def update_profile(self, user_id: str, data: dict) -> dict:
        """No-op in JSON mode — profiles aren't persisted locally."""
        return data

    def save_job(self, data: dict, user_id: str = None) -> dict:
        """No-op in JSON mode — jobs aren't saved separately."""
        return data


# ──────────────────────────────────────────────
# Factory function
# ──────────────────────────────────────────────

# WHY a cached singleton? Creating a new Supabase client on every
# request would be wasteful. The client is thread-safe and reusable.
_db_instance = None


def get_db():
    """Get the database client (Supabase or JSON fallback).

    Checks for SUPABASE_URL in environment variables.
    If set, uses Supabase. Otherwise, falls back to JSON files.

    Returns:
        SupabaseDB or JsonDB instance.
    """
    global _db_instance
    if _db_instance is not None:
        return _db_instance

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if supabase_url and supabase_key:
        _db_instance = SupabaseDB()
        print("📦 Database: Supabase PostgreSQL")
    else:
        _db_instance = JsonDB()
        print("📦 Database: JSON file fallback (set SUPABASE_URL to use PostgreSQL)")

    return _db_instance
