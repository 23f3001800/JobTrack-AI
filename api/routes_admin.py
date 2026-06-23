"""Admin routes — system stats, user management, bulk operations.

WHY separate admin routes?
1. Clear separation of concerns (user routes vs admin routes)
2. All routes in this file require admin auth (require_admin dependency)
3. Easy to disable in production if needed
4. Audit trail: admin actions are logged separately

Access control:
- JWT users with role="admin" in their profile
- API key holders (API key implies admin access)
"""
from fastapi import APIRouter, Depends

from api.auth import AuthUser, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_stats(admin: AuthUser = Depends(require_admin)):
    """System-wide statistics for the admin dashboard.

    Returns aggregate counts: total applications, by status,
    average quality scores, and user count.
    """
    from db import get_db
    db = get_db()

    # Get all applications (admin sees everything)
    all_apps = db.get_applications()

    # Calculate status breakdown
    status_counts = {}
    total_quality = 0
    quality_count = 0

    for app in all_apps:
        status = app.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        score = app.get("quality_score", 0)
        if score > 0:
            total_quality += score
            quality_count += 1

    avg_quality = round(total_quality / quality_count, 1) if quality_count else 0

    return {
        "total_applications": len(all_apps),
        "by_status": status_counts,
        "average_quality_score": avg_quality,
        "quality_rated_count": quality_count,
    }


@router.get("/applications")
async def get_all_applications(admin: AuthUser = Depends(require_admin)):
    """Fetch all applications across all users.

    WHY an admin-only endpoint?
    Regular users should only see their own data (enforced by RLS).
    This endpoint bypasses user scoping for admin oversight.
    """
    from db import get_db
    db = get_db()
    applications = db.get_applications()  # No user_id filter = all apps
    return {"applications": applications, "total": len(applications)}
