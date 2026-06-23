"""Writer Agent — Content generation for job applications.

Responsibility: Generate all written application materials:
- Tailored CV bullet points
- Personalised cover letter
- LinkedIn outreach DM
- (Future: Full PDF resume)

Model: Claude Sonnet (quality matters most for writing)
Tools: tailor_cv_bullets, write_cover_letter, write_outreach_dm

Quality loop: If the Quality Agent provides feedback, the Writer
uses it to rewrite materials. The feedback is passed via
state['quality_feedback'].
"""
from tools.executor import execute_tool
from langsmith import traceable


@traceable(name="writer-agent", tags=["agent", "writer"])
def run_writer(state: dict) -> dict:
    """Generate or rewrite application materials.

    WHY call all 3 tools sequentially instead of letting LLM decide?
    The writing order is fixed: bullets → cover letter → DM.
    Each output feeds into the next (cover letter uses bullets,
    DM uses company profile). No LLM routing needed.

    On REWRITE (quality_feedback exists):
    Only regenerates cover_letter and tailored_bullets — the DM
    is less critical and rewriting it wastes tokens.
    """
    job_analysis = state.get("job_analysis", "")
    company_profile = state.get("company_profile", "")
    role_fit = state.get("role_fit", "")
    quality_feedback = state.get("quality_feedback", "")
    is_rewrite = bool(quality_feedback)

    updates: dict = {}

    # Step 1: Tailor CV bullets
    # WHY pass role_fit as part of company_profile?
    # The tailor_cv_bullets tool takes company_profile as context.
    # Including role_fit helps the LLM focus on matching skills
    # and addressing gaps identified in the fit analysis.
    enriched_profile = company_profile
    if role_fit:
        enriched_profile += f"\n\nROLE FIT ANALYSIS:\n{role_fit}"
    if quality_feedback and is_rewrite:
        enriched_profile += (
            "\n\nPREVIOUS REVIEW FEEDBACK (address these issues):\n"
            + quality_feedback
        )

    tailored_bullets = execute_tool(
        "tailor_cv_bullets",
        {"job_requirements": job_analysis, "company_profile": enriched_profile},
    )
    updates["tailored_bullets"] = tailored_bullets

    # Step 2: Write cover letter
    cover_letter = execute_tool(
        "write_cover_letter",
        {
            "job_analysis": job_analysis,
            "company_profile": company_profile,
            "tailored_bullets": tailored_bullets,
        },
    )
    updates["cover_letter"] = cover_letter

    # Step 3: Write outreach DM (skip on rewrite — not worth the tokens)
    if not is_rewrite and not state.get("outreach_dm"):
        company_name = _extract_field(job_analysis, "COMPANY")
        job_title = _extract_field(job_analysis, "JOB TITLE")
        outreach_dm = execute_tool(
            "write_outreach_dm",
            {
                "company_name": company_name or "the company",
                "job_title": job_title or "the role",
                "company_profile": company_profile,
            },
        )
        updates["outreach_dm"] = outreach_dm

    # Clear quality feedback after rewrite so the quality agent
    # evaluates the new version, not the old feedback
    if is_rewrite:
        updates["quality_feedback"] = ""
        updates["quality_score"] = 0  # Reset score for re-evaluation

    return {
        **updates,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"[Writer] {'Rewrote' if is_rewrite else 'Generated'}"
                    " application materials"
                ),
            }
        ],
        "iterations": state.get("iterations", 0) + 1,
    }


def _extract_field(text: str, field_name: str) -> str:
    """Extract a field value from structured text by label."""
    for line in text.split("\n"):
        if line.strip().upper().startswith(f"{field_name.upper()}:"):
            return line.split(":", 1)[1].strip()
    return ""
