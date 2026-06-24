"""Apply Agent — Application submission and logging.

Responsibility: Log the completed application to storage.
Future phases will add: form detection, auto-fill, screenshot
confirmation, and actual submission via Playwright.

Model: None (deterministic for now)
Tools: log_application, (future: detect_form, fill_and_submit)
"""
from tools.executor import execute_tool
from langsmith import traceable


@traceable(name="apply-agent", tags=["agent", "applier"])
def run_applier(state: dict) -> dict:
    """Log the application with all generated materials.

    WHY deterministic (no LLM)? Logging is a mechanical operation —
    collect all outputs and save them. No reasoning needed.
    When auto-apply is added in Phase 12, this will become
    LLM-powered for form analysis and field mapping.
    """
    job_analysis = state.get("job_analysis", "")
    company_profile = state.get("company_profile", "")

    # Extract company name and job title from the job analysis
    company_name = _extract_field(job_analysis, "COMPANY")
    job_title = _extract_field(job_analysis, "JOB TITLE")

    result = execute_tool(
        "log_application",
        {
            "company": company_name or "Unknown Company",
            "job_title": job_title or "Unknown Role",
            "job_url": state.get("job_url", ""),
            "cover_letter": state.get("cover_letter", ""),
            "tailored_bullets": state.get("tailored_bullets", ""),
            "outreach_dm": state.get("outreach_dm", ""),
            "job_analysis": job_analysis,
            "company_profile": company_profile,
            "role_fit": state.get("role_fit", ""),
            "quality_score": state.get("quality_score", 0),
            "quality_feedback": state.get("quality_feedback", ""),
            "resume_pdf_url": state.get("resume_pdf_url", ""),
            "user_id": state.get("user_id", ""),
            "status": "draft",  # Human-in-the-loop: start as draft
        },
    )

    return {
        "log_result": result,
        "messages": [{"role": "assistant", "content": f"[Applier] {result}"}],
        "iterations": state.get("iterations", 0) + 1,
    }


def _extract_field(text: str, field_name: str) -> str:
    """Extract a field value from structured text by label."""
    for line in text.split("\n"):
        if line.strip().upper().startswith(f"{field_name.upper()}:"):
            return line.split(":", 1)[1].strip()
    return ""
