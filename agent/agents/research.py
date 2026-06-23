"""Research Agent — Company research and role fit analysis.

Responsibility: Build company profile + analyze candidate-role fit.
Runs BOTH research_company and analyze_role_fit in sequence.

Model: Claude Haiku (research synthesis doesn't need Sonnet)
Tools: research_company, analyze_role_fit
"""
from tools.executor import execute_tool
from langsmith import traceable


@traceable(name="research-agent", tags=["agent", "research"])
def run_research(state: dict) -> dict:
    """Research company and analyze role fit.

    WHY run both tools here instead of separate nodes?
    Company research and role fit analysis are tightly coupled —
    the role fit analysis uses the company profile as context.
    Running them together in one node reduces LangGraph iterations
    and keeps the graph simpler.
    """
    job_analysis = state.get("job_analysis", "")
    user_background = state.get("user_background", "")
    updates: dict = {}

    # Step 1: Research the company (if not already done)
    if not state.get("company_profile"):
        # WHY extract company name from job_analysis instead of passing it?
        # The job_analysis contains the structured extraction with COMPANY field.
        # We parse it here so the user doesn't need to provide it separately.
        company_name = _extract_company_name(job_analysis)
        job_title = _extract_job_title(job_analysis)

        company_profile = execute_tool(
            "research_company",
            {"company_name": company_name, "job_title": job_title},
        )
        updates["company_profile"] = company_profile

    # Step 2: Analyze role fit
    if not state.get("role_fit"):
        role_fit = execute_tool(
            "analyze_role_fit",
            {
                "job_analysis": job_analysis,
                "user_background": user_background,
            },
        )
        updates["role_fit"] = role_fit

    return {
        **updates,
        "messages": [
            {
                "role": "assistant",
                "content": "[Research] Company researched, role fit analyzed",
            }
        ],
        "iterations": state.get("iterations", 0) + 1,
    }


def _extract_company_name(job_analysis: str) -> str:
    """Extract company name from the structured job analysis text.

    WHY regex-free? The job analysis format isn't guaranteed —
    different scrapes produce different formats. Simple string
    search for 'COMPANY:' is more robust than regex here.
    Falls back to first line if pattern not found.
    """
    for line in job_analysis.split("\n"):
        line_stripped = line.strip()
        if line_stripped.upper().startswith("COMPANY:"):
            return line_stripped.split(":", 1)[1].strip()
    # Fallback: return first non-empty line (likely the company header)
    for line in job_analysis.split("\n"):
        if line.strip():
            return line.strip()[:50]
    return "Unknown Company"


def _extract_job_title(job_analysis: str) -> str:
    """Extract job title from the structured job analysis text."""
    for line in job_analysis.split("\n"):
        line_stripped = line.strip()
        if line_stripped.upper().startswith("JOB TITLE:"):
            return line_stripped.split(":", 1)[1].strip()
    return ""
