"""FastAPI application — AutoApply AI REST API.

Serves three audiences:
1. Web dashboard (Next.js frontend) — JWT-authenticated user requests
2. MCP server (Claude Desktop) — API key-authenticated tool calls
3. CLI tools and CI/CD — API key-authenticated automation

Architecture:
- /auth/*   → Signup, login, profile management (routes_auth.py)
- /admin/*  → System stats, user management (routes_admin.py)
- /run      → Multi-agent pipeline execution (streaming NDJSON)
- /tracker  → Application history
- /health   → Health check
"""
import json
import uuid

from fastapi import FastAPI, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from agent.graph import app as agent_app, JobState
from dotenv import load_dotenv

from api.auth import AuthUser, verify_user
from api.routes_auth import router as auth_router
from api.routes_admin import router as admin_router
from api.routes_jobs import router as jobs_router
from api.middleware import RequestLoggingMiddleware, ErrorHandlingMiddleware

load_dotenv()


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="AutoApply AI",
    version="3.0.0",
    description="Multi-agent job application system with Supabase backend",
)
app.state.limiter = limiter
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# WHY this order? Middleware runs in REVERSE registration order.
# So ErrorHandling wraps RequestLogging wraps the route handler.
# Errors are caught first, then logged with timing.
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# Register route modules
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(jobs_router)


def _resolve_app_id(app_id: str, db, user_id: str = None) -> str:
    """Resolve app_id to actual DB id.

    WHY? The frontend may send an array index (e.g., "5") when the app
    was loaded by position, but Supabase needs the UUID. This helper
    converts integer indices to UUIDs by looking up the app list.
    For JsonDB (has tracker_path), returns app_id as-is (indices are valid).
    """
    if hasattr(db, "tracker_path"):
        return app_id  # JsonDB uses indices directly

    # If it already looks like a UUID (contains dashes), return as-is
    if "-" in app_id and len(app_id) > 20:
        return app_id

    # It's a numeric index — resolve to UUID
    try:
        idx = int(app_id)
        # Try with user filter first
        all_apps = db.get_applications(user_id=user_id)
        if 0 <= idx < len(all_apps) and all_apps[idx].get("id"):
            return str(all_apps[idx]["id"])

        # Try without user filter (admin/service key case)
        if user_id:
            all_apps = db.get_applications(user_id=None)
            if 0 <= idx < len(all_apps) and all_apps[idx].get("id"):
                return str(all_apps[idx]["id"])
    except (ValueError, IndexError):
        pass

    import logging
    logging.getLogger("autoapply").warning(
        "Could not resolve app_id=%s to UUID (user_id=%s)", app_id, user_id
    )
    return app_id  # Will likely fail at Supabase but provides error info


class RunRequest(BaseModel):
    job_url:         str = Field(..., description="URL of the job posting")
    user_background: str = Field("Python developer", max_length=1000)
    job_description: str = Field("", description="Pre-fetched job description (skips scraping)")

# Field names → human-readable step labels for the client UI.
# WHY track these? The streaming endpoint compares state snapshots
# to detect which field just got populated, then sends that label
# to the frontend for real-time progress updates.
STEP_LABELS = {
    "job_analysis":     "Job analysis",
    "company_profile":  "Company research",
    "role_fit":         "Role fit analysis",
    "tailored_bullets": "CV tailoring",
    "cover_letter":     "Cover letter",
    "outreach_dm":      "LinkedIn DM",
    "resume_pdf_url":   "Resume PDF generated",
    "log_result":       "Application saved as draft",
}

@app.post("/run", tags=["agent"])
@limiter.limit("5/minute")   # Each run costs $0.10–0.50 in API calls
async def run_agent(request: Request, body: RunRequest,
                    user: AuthUser = Depends(verify_user)):
    """Execute the multi-agent pipeline on a job URL.

    Returns a streaming NDJSON response with step-by-step progress.
    Each line is a JSON object: {"step": "...", "status": "done", "preview": "..."}

    WHY streaming instead of a single response?
    The pipeline takes 30-60 seconds. Streaming lets the frontend
    show real-time progress ("Scraping job...", "Researching company...").
    """
    thread_id = body.job_url.split("/")[-1] + "-" + str(uuid.uuid4())[:4]

    # If user is JWT-authenticated, use their profile data
    background = body.user_background
    cv_text = ""
    user_profile = {}  # Full profile for resume generator
    if user.is_authenticated:
        from db import get_db
        profile = get_db().get_profile(user.user_id)
        if not body.user_background:
            background = profile.get("background", body.user_background)
        cv_text = profile.get("cv_text", "")
        user_profile = profile  # Pass full profile for PDF generation

    # Initialize all state fields — includes resume generation and user profile
    initial = JobState(
        job_url=body.job_url, user_background=background,
        cv_text=cv_text, user_id=user.user_id or "",
        user_profile=user_profile,
        job_description_text=body.job_description,
        job_analysis="", company_profile="", role_fit="",
        tailored_bullets="", cover_letter="", outreach_dm="",
        resume_pdf_path="", resume_pdf_url="",
        quality_score=0, quality_feedback="", quality_attempts=0,
        log_result="", messages=[], iterations=0,
    )
    config = {"configurable": {"thread_id": thread_id}}
    async def stream_steps():
        prev_state = {}
        try:
            # WHY stream_mode="values"?
            # Yields the full state after every node execution.
            # We compare current vs previous state to detect
            # which field was just populated — that's the
            # completed step we report to the client.
            async for state in agent_app.astream(
                initial, config=config, stream_mode="values"
            ):
                for field, label in STEP_LABELS.items():
                    if state.get(field) and not prev_state.get(field):
                        chunk = {
                            "step": label,
                            "status": "done",
                            "preview": state[field][:120].replace("\n"," ")
                        }
                        yield json.dumps(chunk) + "\n"
                prev_state = dict(state)
            # Final summary line
            yield json.dumps({
                "step": "complete", "status": "done",
                "thread_id": thread_id,
                "user_id": user.user_id,
                "files": "Check workspace/ directory"
            }) + "\n"

        except Exception as e:
            yield json.dumps({"step": "error", "message": str(e)}) + "\n"

    return StreamingResponse(stream_steps(),
                             media_type="application/x-ndjson")


class BatchRunRequest(BaseModel):
    jobs: list = Field(..., description="List of jobs to apply to")
    auto_mode: bool = Field(False, description="Auto-submit without review")


@app.post("/batch/run", tags=["batch"])
@limiter.limit("2/minute")
async def batch_run(request: Request, body: BatchRunRequest,
                    user: AuthUser = Depends(verify_user)):
    """Execute the pipeline on multiple jobs sequentially.

    Streams NDJSON with batch progress updates.
    Each job gets its own pipeline run.
    """
    # Get user profile
    from db import get_db
    profile = get_db().get_profile(user.user_id)
    background = profile.get("background", "")
    cv_text = profile.get("cv_text", "")
    user_profile = profile

    total = len(body.jobs)

    async def stream_batch():
        for idx, job in enumerate(body.jobs):
            job_url = job.get("url", "")
            job_desc = job.get("description", "")
            job_title = job.get("title", "Unknown")
            job_company = job.get("company", "Unknown")

            # Batch progress header
            yield json.dumps({
                "step": "batch_progress",
                "current": idx + 1,
                "total": total,
                "job_title": job_title,
                "job_company": job_company,
            }) + "\n"

            thread_id = f"batch-{uuid.uuid4().hex[:8]}"

            # Set status based on auto_mode
            initial = JobState(
                job_url=job_url, user_background=background,
                cv_text=cv_text, user_id=user.user_id or "",
                user_profile=user_profile,
                job_description_text=job_desc,
                job_analysis="", company_profile="", role_fit="",
                tailored_bullets="", cover_letter="", outreach_dm="",
                resume_pdf_path="", resume_pdf_url="",
                quality_score=0, quality_feedback="", quality_attempts=0,
                log_result="", messages=[], iterations=0,
            )
            config = {"configurable": {"thread_id": thread_id}}

            try:
                prev_state = {}
                async for state in agent_app.astream(
                    initial, config=config, stream_mode="values"
                ):
                    for field, label in STEP_LABELS.items():
                        if state.get(field) and not prev_state.get(field):
                            yield json.dumps({
                                "step": label,
                                "status": "done",
                                "batch_index": idx + 1,
                                "preview": state[field][:120].replace("\n", " ")
                            }) + "\n"
                    prev_state = dict(state)

                yield json.dumps({
                    "step": "job_complete",
                    "batch_index": idx + 1,
                    "job_title": job_title,
                    "status": "applied" if body.auto_mode else "draft",
                }) + "\n"

            except Exception as e:
                yield json.dumps({
                    "step": "job_error",
                    "batch_index": idx + 1,
                    "job_title": job_title,
                    "message": str(e),
                }) + "\n"

        yield json.dumps({
            "step": "batch_complete",
            "total": total,
        }) + "\n"

    return StreamingResponse(stream_batch(), media_type="application/x-ndjson")


@app.get("/tracker", tags=["tracker"])
async def get_tracker(user: AuthUser = Depends(verify_user)):
    """Return tracked job applications.

    WHY scope by user? JWT-authenticated users only see their own data.
    API key users (admin) see everything.
    """
    from db import get_db
    db = get_db()
    # JWT users see only their apps; API key users see all
    user_id = user.user_id if user.is_authenticated else None
    applications = db.get_applications(user_id=user_id)
    return {"applications": applications, "total": len(applications)}


@app.patch("/tracker/{app_id}/status", tags=["tracker"])
async def update_status(app_id: str, status: str,
                        user: AuthUser = Depends(verify_user)):
    """Update an application's status (for Kanban drag-and-drop).

    WHY a separate endpoint instead of a generic PATCH?
    Status changes are the most common update. A dedicated endpoint
    means the frontend can fire a simple PATCH with just the new status,
    and the backend validates the enum value.
    """
    valid_statuses = [
        "draft", "saved", "applied", "screening", "interview",
        "offer", "rejected", "withdrawn",
    ]
    if status not in valid_statuses:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    from db import get_db
    db = get_db()
    resolved_id = _resolve_app_id(app_id, db, user.user_id if user.is_authenticated else None)
    updated = db.update_application_status(resolved_id, status)
    return {"message": "Status updated", "application": updated}


@app.delete("/tracker/{app_id}", tags=["tracker"])
async def delete_application(app_id: str,
                             user: AuthUser = Depends(verify_user)):
    """Delete an application from the tracker.

    WHY allow deleting? Users may have test entries, duplicates,
    or withdrawn applications they want to clean up. Soft-delete
    (status=withdrawn) is preferred, but hard delete is also useful.
    """
    from db import get_db
    db = get_db()

    # JsonDB: filter out by index or id
    if hasattr(db, "tracker_path"):
        import json
        with open(db.tracker_path) as f:
            apps = json.load(f)

        original_len = len(apps)
        apps = [
            a for i, a in enumerate(apps)
            if str(a.get("id", i)) != app_id and str(i) != app_id
        ]

        if len(apps) == original_len:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Application not found")

        with open(db.tracker_path, "w") as f:
            json.dump(apps, f, indent=2)

        return {"message": "Application deleted", "id": app_id}

    # SupabaseDB
    import logging
    logger = logging.getLogger("autoapply")
    user_id = user.user_id if user.is_authenticated else None
    resolved_id = _resolve_app_id(app_id, db, user_id)
    logger.info("DELETE app_id=%s resolved_id=%s user_id=%s", app_id, resolved_id, user_id)

    try:
        result = db.client.table("applications").delete().eq("id", resolved_id).execute()
        deleted_count = len(result.data) if result.data else 0
        logger.info("Deleted %d rows for id=%s", deleted_count, resolved_id)
        return {"message": "Application deleted", "id": resolved_id, "deleted": deleted_count}
    except Exception as e:
        logger.error("Delete failed for id=%s: %s", resolved_id, e)
        # If resolved_id is not a valid UUID, Supabase throws — give a clear error
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Could not delete application '{app_id}' (resolved to '{resolved_id}'): {e}"
        )


class NotesUpdate(BaseModel):
    notes: str = Field(default="", max_length=5000)


@app.patch("/tracker/{app_id}/notes", tags=["tracker"])
async def update_notes(app_id: str, body: NotesUpdate,
                       user: AuthUser = Depends(verify_user)):
    """Update an application's notes/comments.

    WHY a dedicated notes endpoint?
    Notes are free-form text that users add manually (recruiter name,
    interview date, follow-up reminders). Separating from status
    lets us validate and store notes independently.
    """
    from db import get_db
    db = get_db()

    # JsonDB: update by index or id
    if hasattr(db, "tracker_path"):
        import json as _json
        with open(db.tracker_path) as f:
            apps = _json.load(f)

        updated = False
        for i, a in enumerate(apps):
            if str(a.get("id", i)) == app_id or str(i) == app_id:
                apps[i]["notes"] = body.notes
                updated = True
                break

        if not updated:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Application not found")

        with open(db.tracker_path, "w") as f:
            _json.dump(apps, f, indent=2)

        return {"message": "Notes updated", "id": app_id, "notes": body.notes}

    # SupabaseDB
    resolved_id = _resolve_app_id(app_id, db, user.user_id if user.is_authenticated else None)
    db.client.table("applications").update(
        {"notes": body.notes}
    ).eq("id", resolved_id).execute()
    return {"message": "Notes updated", "id": resolved_id, "notes": body.notes}


class FieldsUpdate(BaseModel):
    """Editable application content fields for the review page."""
    cover_letter: str | None = None
    tailored_bullets: str | None = None
    outreach_dm: str | None = None


@app.patch("/tracker/{app_id}/fields", tags=["tracker"])
async def update_fields(app_id: str, body: FieldsUpdate,
                        user: AuthUser = Depends(verify_user)):
    """Update editable content fields on a draft application.

    WHY a separate endpoint? The review page lets users edit cover letter,
    CV bullets, and outreach DM before submission. These fields are
    content-heavy and need different validation than status or notes.
    """
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No fields to update")

    from db import get_db
    db = get_db()

    # JsonDB: update by index or id
    if hasattr(db, "tracker_path"):
        import json as _json
        with open(db.tracker_path) as f:
            apps = _json.load(f)

        updated = False
        for i, a in enumerate(apps):
            if str(a.get("id", i)) == app_id or str(i) == app_id:
                apps[i].update(update_data)
                updated = True
                break

        if not updated:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Application not found")

        with open(db.tracker_path, "w") as f:
            _json.dump(apps, f, indent=2)

        return {"message": "Fields updated", "id": app_id}

    # SupabaseDB
    resolved_id = _resolve_app_id(app_id, db, user.user_id if user.is_authenticated else None)
    db.client.table("applications").update(
        update_data
    ).eq("id", resolved_id).execute()
    return {"message": "Fields updated", "id": resolved_id}


@app.post("/generate-pdf", tags=["pdf"])
async def generate_pdf(
    name: str, job_title: str, company: str,
    tailored_bullets: str, email: str = "", phone: str = "",
    background: str = "", role_fit: str = "",
    user: AuthUser = Depends(verify_user),
):
    """Generate a tailored PDF resume on demand.

    WHY a separate endpoint instead of always generating in the pipeline?
    Users may want to regenerate a PDF after editing their bullets,
    or generate a PDF for an application they created manually.
    """
    import os
    from tools.pdf_generator import generate_resume_pdf

    workspace = os.getenv("WORKSPACE_DIR", "./workspace")
    filepath = generate_resume_pdf(
        name=name, email=email, phone=phone, background=background,
        tailored_bullets=tailored_bullets, job_title=job_title,
        company=company, role_fit=role_fit, output_dir=workspace,
    )
    return {"message": "PDF generated", "filepath": filepath}


@app.get("/download/{filename}", tags=["pdf"])
async def download_file(filename: str, user: AuthUser = Depends(verify_user)):
    """Download a generated file (PDF, cover letter, etc.) from workspace/.

    WHY validate the filename?
    Prevent path traversal attacks — users could try to access
    ../../../etc/passwd. We only serve files from the workspace directory.
    """
    import os
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    workspace = os.getenv("WORKSPACE_DIR", "./workspace")
    filepath = os.path.join(workspace, filename)

    # Security: ensure the resolved path is inside workspace
    real_workspace = os.path.realpath(workspace)
    real_filepath = os.path.realpath(filepath)
    if not real_filepath.startswith(real_workspace):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(filepath, filename=filename)


class InterviewPrepRequest(BaseModel):
    job_analysis: str = Field(..., description="Job posting analysis")
    company_profile: str = Field("", description="Company research")
    role_fit: str = Field("", description="Role fit analysis")


@app.post("/interview-prep", tags=["tools"])
async def interview_prep(
    body: InterviewPrepRequest,
    user: AuthUser = Depends(verify_user),
):
    """Generate tailored interview questions for a job application.

    WHY a separate endpoint instead of adding to the pipeline?
    Interview prep is a post-application activity. Not every user
    wants it automatically — some prefer to prep only for roles
    where they get a callback.
    """
    from tools.interview_prep import generate_interview_prep

    prep = generate_interview_prep(
        job_analysis=body.job_analysis,
        company_profile=body.company_profile,
        role_fit=body.role_fit,
    )
    return {"prep": prep}


class FollowupRequest(BaseModel):
    company: str = Field(..., description="Company name")
    job_title: str = Field(..., description="Job title")
    days_since_applied: int = Field(7, description="Days since applying")
    cover_letter_excerpt: str = Field("", description="Original cover letter excerpt")
    channel: str = Field("email", description="'email' or 'linkedin'")


@app.post("/followup", tags=["tools"])
async def followup(
    body: FollowupRequest,
    user: AuthUser = Depends(verify_user),
):
    """Generate a context-aware follow-up message."""
    from tools.followup import generate_followup

    result = generate_followup(
        company=body.company,
        job_title=body.job_title,
        days_since_applied=body.days_since_applied,
        cover_letter_excerpt=body.cover_letter_excerpt,
        channel=body.channel,
    )
    return result


@app.get("/export/csv", tags=["tools"])
async def export_csv(user: AuthUser = Depends(verify_user)):
    """Export all applications as a downloadable CSV file.

    WHY server-side CSV instead of just client-side?
    CLI and MCP users can't run JavaScript. A server-side endpoint
    lets automation tools, CI/CD, and scripts download data too.
    """
    import csv
    import io

    from db import get_db
    db = get_db()

    apps_data = db.get_applications(user_id=user.user_id)
    if isinstance(apps_data, dict):
        apps = apps_data.get("applications", [])
    else:
        apps = apps_data

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Company", "Position", "Status", "Quality Score", "Applied Date"])

    for app_item in apps:
        writer.writerow([
            app_item.get("company", ""),
            app_item.get("job_title", ""),
            app_item.get("status", "applied"),
            app_item.get("quality_score", ""),
            app_item.get("applied_at", ""),
        ])

    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=autoapply_export.csv"},
    )


class AutoFillRequest(BaseModel):
    job_url: str
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    cover_letter: str = ""
    resume_path: str = ""
    headless: bool = True


@app.post("/autofill", tags=["automation"])
async def autofill_application(
    body: AutoFillRequest,
    user: AuthUser = Depends(verify_user),
):
    """Auto-fill a job application using Playwright browser automation.

    WHY an API endpoint instead of only a tool?
    The dashboard can trigger auto-fill with one click. The API
    endpoint also allows MCP/CLI users to automate submissions.
    The browser runs server-side (headless Chromium).
    """
    from tools.autofill import auto_fill_application

    user_data = {
        "name": body.name,
        "email": body.email,
        "phone": body.phone,
        "linkedin": body.linkedin,
        "cover_letter": body.cover_letter,
    }

    result = await auto_fill_application(
        job_url=body.job_url,
        user_data=user_data,
        resume_path=body.resume_path if body.resume_path else None,
        headless=body.headless,
    )

    return result


@app.get("/health")
def health():
    """Health check endpoint — no auth required."""
    return {"status": "ok", "mcp_tools": 7, "version": "4.2.0",
            "agents": ["scout", "research", "writer", "quality", "applier"],
            "tools": 14, "endpoints": 22, "tests": 20}