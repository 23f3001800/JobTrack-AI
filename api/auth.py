"""Authentication middleware — dual-mode (Supabase JWT or API key).

WHY two auth modes?
- Supabase JWT: For the web dashboard (frontend sends user's JWT)
- API key: For MCP server, CLI tools, and CI/CD (no user session)

The verify_user() dependency extracts user_id from JWT if available,
or falls back to API key validation. This means:
- Dashboard requests include user_id → data is scoped to that user
- API key requests have user_id=None → admin-level access

Security model:
- JWTs are verified by checking the signature against SUPABASE_JWT_SECRET
- API keys are compared against the API_KEY env var
- Both use Bearer token format: Authorization: Bearer <token>
"""
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

security = HTTPBearer()


class AuthUser:
    """Represents an authenticated user.

    WHY a class instead of just returning user_id string?
    We need to carry both user_id and role for RBAC checks.
    A class also makes it easy to add claims later (email, name, etc.)
    """

    def __init__(self, user_id: Optional[str], role: str = "user",
                 email: str = "", auth_method: str = "api_key"):
        self.user_id = user_id
        self.role = role
        self.email = email
        self.auth_method = auth_method  # "jwt" or "api_key"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_authenticated(self) -> bool:
        """True if user has a real user_id (JWT auth, not just API key)."""
        return self.user_id is not None


def _verify_jwt(token: str) -> Optional[dict]:
    """Verify a Supabase JWT and extract claims.

    WHY verify locally instead of calling Supabase API?
    - Faster: No network round-trip on every request
    - Cheaper: No API calls consumed
    - Offline-capable: Works even if Supabase is momentarily down

    Returns:
        Dict with user claims (sub, email, role) or None if invalid.
    """
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        # No JWT secret configured — can't verify JWTs
        return None

    try:
        import jwt as pyjwt
        payload = pyjwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except Exception:
        # Invalid token, expired, wrong audience, etc.
        return None


def _verify_api_key(token: str) -> bool:
    """Check if the token matches the configured API key."""
    api_key = os.getenv("API_KEY", "dev-key")
    return token == api_key


async def verify_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """FastAPI dependency: authenticate the request and return AuthUser.

    Authentication flow:
    1. Try JWT verification first (for dashboard users)
    2. Fall back to API key check (for CLI/MCP/CI)
    3. Reject if neither works

    WHY try JWT first?
    JWTs are self-contained — we can verify them without any network
    calls. API key check is just a string comparison. Trying JWT first
    means dashboard users get proper user_id scoping.
    """
    token = creds.credentials

    # 1. Try Supabase JWT
    claims = _verify_jwt(token)
    if claims:
        return AuthUser(
            user_id=claims.get("sub"),
            email=claims.get("email", ""),
            role=claims.get("user_metadata", {}).get("role", "user"),
            auth_method="jwt",
        )

    # 2. Fall back to API key
    if _verify_api_key(token):
        return AuthUser(
            user_id=None,  # API key doesn't have a user identity
            role="admin",  # API key holders get admin access
            auth_method="api_key",
        )

    raise HTTPException(status_code=401, detail="Invalid token or API key")


async def require_admin(user: AuthUser = Depends(verify_user)) -> AuthUser:
    """FastAPI dependency: require admin role.

    Use this for admin-only endpoints like viewing all users,
    system stats, or bulk operations.
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
