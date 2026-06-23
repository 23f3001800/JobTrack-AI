"""Quality Agent — Self-review with rewrite feedback loop.

Responsibility: Review generated application materials and either
approve them (score >= 4) or send specific feedback to the Writer
for a rewrite.

Model: Claude Sonnet (nuanced quality judgment requires intelligence)
Tools: review_application, score_quality

This is the MOST IMPORTANT agent for output quality. Without it,
the system produces generic 2-3/5 applications. With it, the
quality loop pushes output to 4-5/5 by catching:
- Generic AI phrases ("resonates deeply", "passionate about")
- Missing company-specific details
- CV bullets that don't match actual job requirements
- Cover letters that could apply to any company
"""
import json

from tools.executor import execute_tool
from langsmith import traceable


@traceable(name="quality-agent", tags=["agent", "quality"])
def run_quality(state: dict) -> dict:
    """Review materials, score quality, and provide rewrite feedback if needed.

    WHY run review AND score in the same node?
    The review provides qualitative feedback ("paragraph 2 is too generic").
    The score provides a quantitative gate (3/5 → rewrite, 4/5 → approve).
    Running both together saves one LangGraph iteration.

    The quality_attempts counter prevents infinite rewrite loops.
    """
    job_analysis = state.get("job_analysis", "")
    company_profile = state.get("company_profile", "")
    cover_letter = state.get("cover_letter", "")
    tailored_bullets = state.get("tailored_bullets", "")
    quality_attempts = state.get("quality_attempts", 0)

    # Step 1: Get detailed review feedback
    review = execute_tool(
        "review_application",
        {
            "job_analysis": job_analysis,
            "company_profile": company_profile,
            "cover_letter": cover_letter,
            "tailored_bullets": tailored_bullets,
        },
    )

    # Step 2: Get numerical score
    score_json = execute_tool(
        "score_quality",
        {
            "job_analysis": job_analysis,
            "company_profile": company_profile,
            "cover_letter": cover_letter,
            "tailored_bullets": tailored_bullets,
        },
    )

    # Parse score from JSON response
    score = _parse_score(score_json)

    updates: dict = {
        "quality_score": score,
        "quality_attempts": quality_attempts + 1,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"[Quality] Score: {score}/5"
                    f" (attempt {quality_attempts + 1})"
                ),
            }
        ],
        "iterations": state.get("iterations", 0) + 1,
    }

    # If score is below threshold, attach feedback for Writer rewrite.
    # WHY threshold of 4? Scores 1-3 indicate generic/mediocre content.
    # Score 4+ means genuinely personalised and role-specific.
    if score < 4:
        updates["quality_feedback"] = review
    else:
        updates["quality_feedback"] = ""  # Clear feedback — approved

    return updates


def _parse_score(score_json: str) -> int:
    """Extract the overall score from the quality JSON response.

    WHY not use json.loads directly? The LLM sometimes wraps JSON
    in markdown code fences or adds preamble text. This robust
    parser handles those edge cases without crashing the pipeline.
    """
    # Strip markdown fences if present
    text = score_json.strip()
    if text.startswith("```json"):
        text = text[len("```json") :].strip()
    elif text.startswith("```"):
        text = text[len("```") :].strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        data = json.loads(text)
        return int(data.get("overall", 3))
    except (json.JSONDecodeError, ValueError, TypeError):
        # WHY default to 3? It's the "uncertain" score — high enough
        # to not trigger an infinite rewrite loop, low enough to
        # not falsely approve garbage output.
        return 3
