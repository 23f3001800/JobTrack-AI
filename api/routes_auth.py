"""Authentication routes — signup proxy, profile management.

WHY proxy Supabase Auth instead of calling it from the frontend directly?
1. The frontend only talks to OUR API — single point of contact
2. We can add custom logic (auto-create profile, attach defaults)
3. Rate limiting is centralized on our server
4. The service key never leaves the backend

The frontend DOES use the Supabase JS client for session management
(token refresh, password reset). These routes handle the initial
auth flow and profile CRUD.
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.auth import AuthUser, verify_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ──────────────────────────────────────────────
# Request/Response schemas
# ──────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    """Fields the user can update on their profile.

    WHY optional fields? The frontend sends only the fields that changed.
    PATCH semantics — not all fields are required.
    """
    full_name: str | None = None
    background: str | None = None
    skills: list[str] | None = None
    cv_text: str | None = None


# ──────────────────────────────────────────────
# Auth endpoints
# ──────────────────────────────────────────────

@router.post("/signup")
async def signup(body: SignupRequest):
    """Create a new user.

    Supports two backends:
    1. Supabase Auth (production) — creates user via admin API
    2. JSON fallback (local dev) — appends to workspace/users.json
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    # ── Supabase Auth (production) ──
    if supabase_url and supabase_key:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)

        try:
            result = client.auth.admin.create_user({
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
            })

            return {
                "user_id": result.user.id,
                "email": result.user.email,
                "message": "Account created successfully",
            }

        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower():
                raise HTTPException(status_code=409, detail="Email already registered")
            raise HTTPException(status_code=400, detail=f"Signup failed: {error_msg}")

    # ── JSON Fallback (local dev) ──
    import hashlib
    import json
    import uuid
    from datetime import datetime
    from pathlib import Path

    workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    workspace.mkdir(parents=True, exist_ok=True)
    users_file = workspace / "users.json"

    users = []
    if users_file.exists():
        with open(users_file) as f:
            users = json.load(f)

    # Check for duplicate email
    if any(u["email"] == body.email for u in users):
        raise HTTPException(status_code=409, detail="Email already registered")

    new_user = {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, body.email)),
        "email": body.email,
        "password_hash": hashlib.sha256(body.password.encode()).hexdigest(),
        "full_name": "",
        "role": "user",
        "background": "",
        "skills": [],
        "cv_text": "",
        "created_at": datetime.now().isoformat(),
    }
    users.append(new_user)

    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)

    return {
        "user_id": new_user["id"],
        "email": new_user["email"],
        "message": "Account created successfully",
    }


@router.post("/login")
async def login(body: LoginRequest):
    """Authenticate user and return JWT tokens.

    Supports two backends:
    1. Supabase Auth (production) — returns real JWTs
    2. JSON fallback (local dev) — returns a simple token from users.json

    WHY support both? Developers shouldn't need Supabase credentials
    just to test the dashboard locally. The JSON fallback verifies
    credentials against the seeded admin user from db/init_db.py.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon = os.getenv("SUPABASE_ANON_KEY")

    # ── Supabase Auth (production) ──
    if supabase_url and supabase_anon:
        from supabase import create_client
        client = create_client(supabase_url, supabase_anon)

        try:
            result = client.auth.sign_in_with_password({
                "email": body.email,
                "password": body.password,
            })

            return {
                "access_token": result.session.access_token,
                "refresh_token": result.session.refresh_token,
                "expires_in": result.session.expires_in,
                "user": {
                    "id": result.user.id,
                    "email": result.user.email,
                },
            }

        except Exception:
            raise HTTPException(status_code=401, detail="Invalid email or password")

    # ── JSON Fallback (local dev) ──
    import hashlib
    import json
    from pathlib import Path

    workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    users_file = workspace / "users.json"

    if not users_file.exists():
        raise HTTPException(
            status_code=503,
            detail="No auth backend configured. Run: python -m db.init_db",
        )

    with open(users_file) as f:
        users = json.load(f)

    password_hash = hashlib.sha256(body.password.encode()).hexdigest()

    for user in users:
        if user["email"] == body.email and user["password_hash"] == password_hash:
            # WHY use the API_KEY as the token?
            # In JSON fallback mode, there's no JWT infrastructure.
            # The API key serves as the auth token — the auth middleware
            # already accepts API keys as Bearer tokens.
            api_key = os.getenv("API_KEY", "dev-secret-key")
            return {
                "access_token": api_key,
                "refresh_token": "",
                "expires_in": 86400,
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "role": user.get("role", "user"),
                },
            }

    raise HTTPException(status_code=401, detail="Invalid email or password")


# ──────────────────────────────────────────────
# Profile endpoints
# ──────────────────────────────────────────────

@router.get("/profile")
async def get_profile(user: AuthUser = Depends(verify_user)):
    """Get the current user's profile.

    WHY require auth? Profile contains private data (background, CV).
    API key users get a stub profile since they don't have user identity.
    """
    from db import get_db
    db = get_db()
    profile = db.get_profile(user.user_id)

    if not profile:
        return {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": "",
            "background": "",
            "skills": [],
            "message": "Profile not yet set up",
        }

    return profile


@router.patch("/profile")
async def update_profile(body: ProfileUpdate,
                         user: AuthUser = Depends(verify_user)):
    """Update the current user's profile fields.

    Only authenticated JWT users can update profiles.
    API key users get a 403 since they don't have a user identity.
    """
    if not user.is_authenticated:
        raise HTTPException(
            status_code=403,
            detail="Profile updates require user authentication (JWT), not API key",
        )

    # Build update dict with only non-None fields (PATCH semantics)
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    from db import get_db
    db = get_db()
    updated = db.update_profile(user.user_id, update_data)

    return {"message": "Profile updated", "profile": updated}
