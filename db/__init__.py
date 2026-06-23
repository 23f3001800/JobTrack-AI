"""Database package for JobTrack AI.

Provides a unified data access layer that works with:
1. Supabase (PostgreSQL) — for production and deployed environments
2. JSON file fallback — for local dev without Supabase credentials

WHY this abstraction?
- Developers can run the app locally without any Supabase setup
- CI tests don't need a database connection
- Production uses Supabase for persistence, auth, and realtime
- The rest of the app doesn't know or care which backend is active
"""

from db.client import get_db

__all__ = ["get_db"]
