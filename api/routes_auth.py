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

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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
    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    default_location: str | None = None


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
        "phone": "",
        "linkedin_url": "",
        "github_url": "",
        "default_location": "",
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

            # Fetch role from profiles table
            # WHY a separate query? Supabase Auth doesn't store custom
            # fields like 'role'. The profiles table holds our RBAC data.
            user_role = "user"
            try:
                service_key = os.getenv("SUPABASE_SERVICE_KEY")
                if service_key:
                    admin_client = create_client(supabase_url, service_key)
                    profile_resp = admin_client.table("profiles").select(
                        "role"
                    ).eq("id", result.user.id).single().execute()
                    if profile_resp.data:
                        user_role = profile_resp.data.get("role", "user")
            except Exception:
                pass  # Default to "user" if profile lookup fails

            return {
                "access_token": result.session.access_token,
                "refresh_token": result.session.refresh_token,
                "expires_in": result.session.expires_in,
                "user": {
                    "id": result.user.id,
                    "email": result.user.email,
                    "role": user_role,
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
            "cv_text": "",
            "phone": "",
            "linkedin_url": "",
            "github_url": "",
            "default_location": "",
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


@router.post("/profile/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: AuthUser = Depends(verify_user),
):
    """Upload a resume PDF. Extracts text and stores it in the profile.

    WHY extract text server-side?
    1. The AI agent needs plain text to generate tailored CVs
    2. pypdf extraction is fast and reliable for most PDF formats
    3. The original PDF is also saved for download/auto-fill attachments

    The extracted text is stored in the `cv_text` profile field.
    The PDF file is saved to workspace/resumes/{user_id}.pdf.
    """
    if not user.is_authenticated:
        raise HTTPException(
            status_code=403,
            detail="Resume upload requires user authentication (JWT)",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read file content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Save PDF to workspace
    from pathlib import Path
    resume_dir = Path(os.getenv("WORKSPACE_DIR", "./workspace")) / "resumes"
    resume_dir.mkdir(parents=True, exist_ok=True)
    resume_path = resume_dir / f"{user.user_id}.pdf"
    with open(resume_path, "wb") as f:
        f.write(content)

    # Extract text using pypdf
    cv_text = ""
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        cv_text = "\n\n".join(pages_text)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract text from PDF: {e}",
        )

    if not cv_text.strip():
        raise HTTPException(
            status_code=422,
            detail="PDF appears to be empty or image-only (no extractable text)",
        )

    # Save extracted text to profile
    from db import get_db
    db = get_db()
    db.update_profile(user.user_id, {
        "cv_text": cv_text,
    })

    return {
        "message": "Resume uploaded and text extracted",
        "cv_text": cv_text,
        "file_path": str(resume_path),
        "pages": len(cv_text.split("\n\n")),
    }
