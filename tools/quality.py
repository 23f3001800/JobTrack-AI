"""Quality Agent tools — the self-review system for application materials.

WHY this module exists:
Without a dedicated quality gate, the agentic pipeline produces generic
AI-sounding content ("I'm passionate about…", "resonates deeply") that
scores 2-3/5 in real evaluations. This module acts as an internal editor,
catching vague phrases, missing company-specific details, and
role-requirement mismatches BEFORE the user ever sees the output.

Architecture note:
Two separate tools exist here because they serve different consumers:
- review_application → prose feedback for the Writer agent's rewrite loop
- score_quality → structured JSON for programmatic quality gates (pass/fail)
Combining them into one prompt degrades both outputs — the model tries to
be structured AND verbose at the same time, doing neither well.
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()


def review_application(job_analysis: str, company_profile: str,
                       cover_letter: str, tailored_bullets: str) -> str:
    """Review all generated application materials and provide specific,
    actionable feedback for improvement.

    WHY this exists: Without a quality gate, the agent produces generic
    AI-sounding content that scores 2-3/5 in evaluations. This tool
    acts as an internal editor — catching vague phrases, missing
    company-specific details, and role-requirement mismatches.

    Args:
        job_analysis: Scraped and parsed job posting requirements.
        company_profile: Researched company background and culture info.
        cover_letter: The generated cover letter to review.
        tailored_bullets: The tailored CV bullet points to review.

    Returns:
        Structured prose feedback with quoted issues, explanations,
        and concrete rewrite suggestions. Starts with "APPROVED" if
        everything passes review.
    """
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{"role": "user", "content":
            f"""You are a senior hiring manager reviewing this job application.

Review each component and provide SPECIFIC, ACTIONABLE feedback.

For each issue found, explain:
1. What's wrong (quote the specific phrase)
2. Why it's a problem
3. How to fix it (with a concrete rewrite suggestion)

Common issues to check:
- Generic phrases like "resonates deeply", "passionate about", "excited to"
- Missing specific details from the company profile
- CV bullets that don't match the actual job requirements
- Cover letter that could apply to ANY company (not personalised)
- Technical claims that don't match the job's tech stack

JOB REQUIREMENTS:
{job_analysis[:800]}

COMPANY PROFILE:
{company_profile[:600]}

COVER LETTER:
{cover_letter}

TAILORED CV BULLETS:
{tailored_bullets}

Provide your review as structured feedback. If everything is excellent, say "APPROVED" at the start."""}]
    )
    return resp.content[0].text


def score_quality(job_analysis: str, company_profile: str,
                  cover_letter: str, tailored_bullets: str) -> str:
    """Score application quality on a 1-5 scale with boolean flags.

    WHY separate from review_application: Scoring needs structured
    JSON output for programmatic quality gates. The review provides
    prose feedback for the rewrite loop. Keeping them separate means
    the scoring prompt can be optimised for consistent JSON output
    without competing with detailed feedback generation.

    Args:
        job_analysis: Scraped and parsed job posting requirements.
        company_profile: Researched company background and culture info.
        cover_letter: The generated cover letter to score.
        tailored_bullets: The tailored CV bullet points to score.

    Returns:
        Raw JSON string with keys: overall (1-5), is_personalised (bool),
        role_matched (bool), professional_tone (bool), reasoning (str).
    """
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content":
            f"""Score this job application on quality. Be strict — mediocre
AI-generated applications score 2-3. Only truly personalised,
role-specific applications score 4-5.

JOB: {job_analysis[:500]}
COMPANY: {company_profile[:400]}
COVER LETTER: {cover_letter[:1500]}
CV BULLETS: {tailored_bullets[:800]}

Respond with ONLY valid JSON — no preamble, no markdown:
{{"overall": 1-5, "is_personalised": true/false, "role_matched": true/false, "professional_tone": true/false, "reasoning": "1-2 sentences"}}"""}]
    )
    return resp.content[0].text
