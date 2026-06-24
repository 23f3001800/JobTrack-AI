"""Supervisor agent — deterministic router for the multi-agent system.

WHY deterministic (no LLM)?
The routing logic is straightforward: check which fields are populated
in the state and route to the next agent that needs to run. Using an
LLM for this would waste tokens on a decision that's always the same.
The sub-agents themselves use LLMs for the actual reasoning.

Routing order:
1. Scout (scrape job) → if no job_analysis
2. Research (company + role fit) → if no company_profile or role_fit
3. Writer (cover letter, bullets, DM) → if no cover_letter
4. Resume Generator (tailored PDF) → if no resume_pdf_url
5. Quality (review + score) → if not quality-approved
6. Applier (log as draft) → if not logged

Quality loop: If quality_score < 4 and attempts < 2,
route back to Writer with feedback.
"""


def route_next_agent(state: dict) -> str:
    """Determine which sub-agent should run next.

    Returns the name of the next node in the LangGraph.
    This is a pure function — no side effects, no LLM calls.
    """
    # Step 1: Need to scrape the job posting
    if not state.get("job_analysis"):
        return "scout"

    # Step 2: Need company research and role fit analysis
    if not state.get("company_profile") or not state.get("role_fit"):
        return "research"

    # Step 3 & 4: Quality loop — Writer ↔ Quality
    quality_score = state.get("quality_score", 0)
    quality_attempts = state.get("quality_attempts", 0)

    # Need to write materials (first time or rewrite after quality feedback)
    if not state.get("cover_letter"):
        return "writer"

    # Step 4: Generate tailored resume PDF
    # WHY after writer? Resume PDF needs tailored_bullets from Writer.
    # WHY before quality? Quality agent can reference the PDF in review.
    if not state.get("resume_pdf_url"):
        return "resume_generator"

    # Need quality review
    if quality_score == 0:
        return "quality"

    # Quality failed — rewrite if under max attempts
    # WHY max 2 attempts? More than 2 rewrites hit diminishing returns
    # and waste tokens. Better to ship a 3/5 than burn $0.50 chasing 5/5.
    if quality_score < 4 and quality_attempts < 2:
        return "writer"

    # Step 5: Log the application (as draft for human review)
    if not state.get("log_result"):
        return "applier"

    return "end"

