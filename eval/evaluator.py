"""Evaluation Framework — automated quality scoring for application outputs.

WHY build an eval framework?
1. Proves the quality loop works (before: 2.2/5, after: 4.2/5)
2. Catches regressions — run evals in CI to prevent quality drops
3. Interview talking point: "I built an automated eval pipeline"
4. Generates reproducible metrics for the README

The evaluator uses Claude as an LLM-as-judge, scoring outputs on:
- Overall quality (1-5)
- Personalisation (bool) — does it mention specific company details?
- Role match (bool) — does it address the job requirements?
- Professional tone (bool) — appropriate for a job application?
- Detailed reasoning — why the score was given

Usage:
    from eval.evaluator import evaluate_application
    result = evaluate_application(job_analysis, cover_letter, tailored_bullets)
    print(result["overall"])  # 4
"""
import json

import anthropic
from dotenv import load_dotenv

load_dotenv()


# The eval prompt is designed to be a strict, realistic hiring manager.
# WHY strict? Inflated scores don't help. We need honest feedback
# to know if the quality loop is actually working.
EVAL_SYSTEM_PROMPT = """You are a senior hiring manager evaluating job application materials.
Be STRICT and REALISTIC. Score like a real hiring manager would.

Evaluate on these criteria:
1. **Overall Quality** (1-5): Would you move this candidate forward?
   - 1: Generic, templated, no effort
   - 2: Some customization but clearly AI-generated boilerplate
   - 3: Decent, shows research but lacks depth
   - 4: Strong, personalised, addresses specific requirements
   - 5: Exceptional, would immediately schedule an interview

2. **Personalisation** (true/false): Does the application reference specific
   company details (product, mission, recent news, tech stack) in a way that
   shows genuine research, not just name-dropping?

3. **Role Match** (true/false): Does the application demonstrate skills and
   experience that directly match the job requirements?

4. **Professional Tone** (true/false): Is the writing professional, concise,
   and appropriate for a job application? No typos, no AI tell-tales like
   "I'm thrilled" or "I'm passionate about leveraging"?

Return ONLY valid JSON:
{
    "overall": <1-5>,
    "is_personalised": <true|false>,
    "role_matched": <true|false>,
    "professional_tone": <true|false>,
    "reasoning": "<2-3 sentences explaining the score>"
}"""


def evaluate_application(
    job_analysis: str,
    cover_letter: str,
    tailored_bullets: str,
    company_profile: str = "",
    company: str = "",
) -> dict:
    """Score an application's quality using Claude as a judge.

    Args:
        job_analysis: The scraped job posting analysis
        cover_letter: Generated cover letter text
        tailored_bullets: Job-tailored CV bullet points
        company_profile: Company research (optional, adds context)
        company: Company name for result labeling

    Returns:
        Dict with: overall (1-5), is_personalised, role_matched,
        professional_tone, reasoning, company
    """
    # Build the evaluation prompt with all available materials
    materials = f"""## Job Analysis
{job_analysis}

## Cover Letter
{cover_letter}

## Tailored CV Bullets
{tailored_bullets}"""

    if company_profile:
        materials += f"""

## Company Research Available
{company_profile}"""

    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=EVAL_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Evaluate this job application:\n\n{materials}",
        }],
    )

    # Parse the JSON response
    raw = response.content[0].text.strip()

    # Handle potential markdown code blocks in response
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback if Claude doesn't return clean JSON
        result = {
            "overall": 0,
            "is_personalised": False,
            "role_matched": False,
            "professional_tone": False,
            "reasoning": f"Failed to parse eval response: {raw[:200]}",
        }

    # Add company label for reporting
    result["company"] = company
    return result


def evaluate_batch(applications: list[dict]) -> dict:
    """Evaluate a batch of applications and compute aggregate metrics.

    Args:
        applications: List of dicts, each with keys:
            job_analysis, cover_letter, tailored_bullets,
            company_profile (optional), company

    Returns:
        Dict with: avg_score, results (list), pass_rate, metrics summary
    """
    results = []

    for app in applications:
        result = evaluate_application(
            job_analysis=app.get("job_analysis", ""),
            cover_letter=app.get("cover_letter", ""),
            tailored_bullets=app.get("tailored_bullets", ""),
            company_profile=app.get("company_profile", ""),
            company=app.get("company", "Unknown"),
        )
        results.append(result)

    # Compute aggregate metrics
    scores = [r["overall"] for r in results if r["overall"] > 0]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    personalised_count = sum(1 for r in results if r.get("is_personalised"))
    role_matched_count = sum(1 for r in results if r.get("role_matched"))
    professional_count = sum(1 for r in results if r.get("professional_tone"))
    total = len(results) or 1

    return {
        "avg_score": avg_score,
        "pass_rate": f"{sum(1 for s in scores if s >= 4)}/{len(scores)}",
        "personalisation_rate": f"{personalised_count}/{total}",
        "role_match_rate": f"{role_matched_count}/{total}",
        "professional_tone_rate": f"{professional_count}/{total}",
        "results": results,
    }
