"""Database initializer — seeds admin user and sets up local DB.

WHY a separate init script?
1. Creates the default admin user on first run
2. Works with both Supabase and JSON fallback
3. Can be run in Docker entrypoint or manually
4. Idempotent — safe to run multiple times

Usage:
    python -m db.init_db

Admin credentials (change in production!):
    Email:    admin@jobtrack.ai
    Password: JobTrack@Admin2024
    Role:     admin
"""
import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Default Admin Credentials ──
# WHY hardcoded defaults? For local dev and first-run convenience.
# In production, override via ADMIN_EMAIL and ADMIN_PASSWORD env vars.
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@jobtrack.ai")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "JobTrack@Admin2024")
ADMIN_NAME = "JobTrack Admin"


def _hash_password(password: str) -> str:
    """Simple SHA-256 hash for JSON fallback mode.

    WHY not bcrypt? The JSON fallback is for LOCAL DEV ONLY.
    Supabase handles proper password hashing in production.
    This is just enough to not store plaintext in tracker files.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def init_supabase():
    """Seed admin user in Supabase Auth + set admin role in profiles."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("⚠️  Supabase not configured — skipping Supabase init")
        return False

    from supabase import create_client
    client = create_client(supabase_url, supabase_key)

    # Check if admin already exists
    try:
        existing = (
            client.table("profiles")
            .select("id, email, role")
            .eq("email", ADMIN_EMAIL)
            .execute()
        )
        if existing.data:
            print(f"✅ Admin already exists: {ADMIN_EMAIL}")
            # Ensure role is admin
            if existing.data[0].get("role") != "admin":
                client.table("profiles").update(
                    {"role": "admin"}
                ).eq("email", ADMIN_EMAIL).execute()
                print("   → Updated role to admin")
            return True
    except Exception:
        pass  # Table might not exist yet

    # Create admin user via Supabase Auth
    try:
        result = client.auth.admin.create_user({
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "email_confirm": True,
            "user_metadata": {"full_name": ADMIN_NAME},
        })

        admin_id = result.user.id

        # The on_auth_user_created trigger creates the profile row,
        # but we need to update the role to 'admin'
        client.table("profiles").update({
            "role": "admin",
            "full_name": ADMIN_NAME,
        }).eq("id", admin_id).execute()

        print("✅ Admin user created in Supabase:")
        print(f"   Email:    {ADMIN_EMAIL}")
        print(f"   Password: {ADMIN_PASSWORD}")
        print("   Role:     admin")
        print(f"   ID:       {admin_id}")
        return True

    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            print(f"✅ Admin already exists: {ADMIN_EMAIL}")
            return True
        print(f"❌ Failed to create admin in Supabase: {e}")
        return False


def init_json_db():
    """Seed admin user in JSON fallback database."""
    workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    workspace.mkdir(parents=True, exist_ok=True)

    users_file = workspace / "users.json"
    admin_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, ADMIN_EMAIL))

    # Load existing users or create new
    if users_file.exists():
        with open(users_file) as f:
            users = json.load(f)
    else:
        users = []

    # Check if admin already exists
    admin_exists = any(u.get("email") == ADMIN_EMAIL for u in users)
    if admin_exists:
        # Ensure role is admin
        for u in users:
            if u.get("email") == ADMIN_EMAIL:
                u["role"] = "admin"
        with open(users_file, "w") as f:
            json.dump(users, f, indent=2)
        print(f"✅ Admin already exists: {ADMIN_EMAIL}")
        return True

    # Create admin user
    admin_user = {
        "id": admin_id,
        "email": ADMIN_EMAIL,
        "password_hash": _hash_password(ADMIN_PASSWORD),
        "full_name": ADMIN_NAME,
        "role": "admin",
        "background": "",
        "skills": [],
        "cv_text": "",
        "created_at": datetime.now().isoformat(),
    }
    users.append(admin_user)

    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)

    print("✅ Admin user created in JSON database:")
    print(f"   Email:    {ADMIN_EMAIL}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print("   Role:     admin")
    print(f"   ID:       {admin_id}")
    print(f"   File:     {users_file}")
    return True


def init_tracker():
    """Ensure tracker.json exists."""
    workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    workspace.mkdir(parents=True, exist_ok=True)
    tracker = workspace / "tracker.json"
    if not tracker.exists():
        with open(tracker, "w") as f:
            json.dump([], f)
        print("📋 Created empty tracker.json")


def main():
    """Initialize the database and seed admin user."""
    print("=" * 50)
    print("🗄️  JobTrack AI — Database Initialization")
    print("=" * 50)
    print()

    # Always init JSON fallback (it's the base layer)
    init_json_db()
    init_tracker()

    # Try Supabase if configured
    init_supabase()

    print()
    print("=" * 50)
    print("🔑 Admin Credentials:")
    print(f"   Email:    {ADMIN_EMAIL}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print("=" * 50)
    print()
    print("⚠️  Change these in production via ADMIN_EMAIL and ADMIN_PASSWORD env vars!")
    print()


if __name__ == "__main__":
    main()
