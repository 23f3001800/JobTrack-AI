"""Resume-to-job matching — auto-generate queries and rank results.

WHY a separate matcher module?
The job_search module handles API calls to providers.
This module handles the INTELLIGENCE layer:
1. Analyzing a user's resume to generate optimal search queries
2. Scoring/ranking discovered jobs by relevance to the user's profile

These are fundamentally different concerns — search is IO-bound (API calls),
matching is compute-bound (LLM reasoning + keyword analysis).
"""
import logging
import os
import re
from typing import Optional

logger = logging.getLogger("autoapply.job_matcher")


def generate_search_queries(parsed_profile: dict) -> list[dict]:
    """Analyze user's resume to generate targeted job search queries.

    Uses Claude to analyze skills, experience, seniority and generate
    3-5 search queries optimized for job search APIs.

    Args:
        parsed_profile: Structured profile from resume parser
            (full_name, skills, experience, education, summary, etc.)

    Returns:
        List of dicts: [{"query": "...", "location": "..."}, ...]

    WHY use an LLM instead of simple keyword extraction?
    A resume saying "Built production ML pipelines with PyTorch" should
    generate "Machine Learning Engineer" not just "PyTorch developer".
    The LLM understands role-level inference from project descriptions.
    """
    # Build a concise profile summary for the LLM
    skills = parsed_profile.get("skills", [])
    experience = parsed_profile.get("experience", [])
    education = parsed_profile.get("education", [])
    summary = parsed_profile.get("summary", "")

    # Format experience entries
    exp_text = ""
    for exp in experience[:5]:  # Limit to avoid token overflow
        if isinstance(exp, dict):
            exp_text += f"- {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})\n"
        elif isinstance(exp, str):
            exp_text += f"- {exp}\n"

    # Format education
    edu_text = ""
    for edu in education[:3]:
        if isinstance(edu, dict):
            edu_text += f"- {edu.get('degree', '')} from {edu.get('institution', '')}\n"
        elif isinstance(edu, str):
            edu_text += f"- {edu}\n"

    profile_summary = f"""
Skills: {', '.join(skills[:20])}
Experience:
{exp_text or 'Fresher / Entry-level'}
Education:
{edu_text or 'Not specified'}
Summary: {summary[:300]}
""".strip()

    # Try LLM-based query generation
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _generate_queries_llm(profile_summary, api_key)
        except Exception as e:
            logger.warning("LLM query generation failed: %s, using keyword fallback", e)

    # Fallback: keyword-based query generation
    return _generate_queries_keyword(parsed_profile)


def _generate_queries_llm(profile_summary: str, api_key: str) -> list[dict]:
    """Use Claude to generate intelligent search queries from profile."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Based on this candidate's profile, generate 3-5 job search queries 
that would find the best matching opportunities. Each query should be a 
concise search string (3-6 words) optimized for job search engines.

PROFILE:
{profile_summary}

Return ONLY a JSON array of objects, each with "query" and "location" fields.
Set location to "remote" if the profile doesn't indicate a location preference.

Example output:
[
  {{"query": "AI Engineer Python LangChain", "location": "remote"}},
  {{"query": "Machine Learning Engineer", "location": "Bengaluru"}},
  {{"query": "Data Scientist NLP", "location": "remote"}}
]

Return ONLY the JSON array, no other text."""
        }],
    )

    import json
    raw = response.content[0].text.strip()
    # Handle markdown-wrapped JSON
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    queries = json.loads(raw)

    # Validate structure
    validated = []
    for q in queries[:5]:
        if isinstance(q, dict) and "query" in q:
            validated.append({
                "query": str(q["query"]),
                "location": str(q.get("location", "remote")),
            })

    return validated if validated else _generate_queries_keyword_from_summary(profile_summary)


def _generate_queries_keyword(parsed_profile: dict) -> list[dict]:
    """Generate search queries from profile keywords (no LLM needed).

    WHY a keyword fallback? If the Anthropic API is unavailable,
    we still need to generate reasonable search queries. Simple
    keyword combination covers most cases.
    """
    skills = parsed_profile.get("skills", [])
    summary = parsed_profile.get("summary", "")
    experience = parsed_profile.get("experience", [])

    queries = []

    # Query 1: Top skills combination
    if skills:
        top_skills = skills[:3]
        queries.append({
            "query": " ".join(top_skills) + " developer",
            "location": "remote",
        })

    # Query 2: Based on experience titles
    for exp in experience[:2]:
        title = ""
        if isinstance(exp, dict):
            title = exp.get("title", "")
        elif isinstance(exp, str):
            title = exp
        if title:
            queries.append({"query": title, "location": "remote"})

    # Query 3: Based on education
    education = parsed_profile.get("education", [])
    for edu in education[:1]:
        degree = ""
        if isinstance(edu, dict):
            degree = edu.get("degree", "")
        elif isinstance(edu, str):
            degree = edu
        if degree and any(kw in degree.lower() for kw in ["data", "computer", "ai", "ml", "software"]):
            queries.append({"query": f"{degree} jobs", "location": "remote"})

    # Query 4: Summary-based
    if summary and not queries:
        # Extract key terms from summary
        words = summary.split()[:6]
        queries.append({"query": " ".join(words), "location": "remote"})

    # Ensure at least one query
    if not queries:
        queries.append({"query": "software engineer", "location": "remote"})

    return queries[:5]


def _generate_queries_keyword_from_summary(profile_summary: str) -> list[dict]:
    """Last-resort query generation from raw summary text."""
    return [{"query": "software engineer", "location": "remote"}]


def rank_jobs(
    jobs: list[dict],
    parsed_profile: dict,
    api_key: Optional[str] = None,
) -> list[dict]:
    """Score and rank jobs by relevance to the user's profile.

    Scoring factors (0-100):
    - Skill match: % of job keywords that match user skills
    - Title match: How well the job title aligns with experience
    - Seniority match: Entry/mid/senior alignment

    WHY not use an LLM for ranking?
    Ranking 20+ jobs with an LLM would be slow and expensive.
    Simple keyword matching is fast and produces good-enough results.
    The LLM is used later for the IMPORTANT task: generating applications.
    """
    user_skills = set(s.lower() for s in parsed_profile.get("skills", []))
    user_summary = (parsed_profile.get("summary", "") or "").lower()

    # Extract experience-related keywords
    exp_keywords = set()
    for exp in parsed_profile.get("experience", []):
        if isinstance(exp, dict):
            for field in ["title", "company", "details"]:
                exp_keywords.update(
                    w.lower() for w in str(exp.get(field, "")).split()
                    if len(w) > 3
                )

    scored_jobs = []
    for job in jobs:
        score = _calculate_relevance(job, user_skills, user_summary, exp_keywords)
        job["relevance_score"] = score
        scored_jobs.append(job)

    # Sort by relevance score (descending)
    scored_jobs.sort(key=lambda j: j["relevance_score"], reverse=True)

    return scored_jobs


def _calculate_relevance(
    job: dict,
    user_skills: set,
    user_summary: str,
    exp_keywords: set,
) -> int:
    """Calculate a 0-100 relevance score for a job against user profile."""
    score = 0
    jd = (job.get("description", "") + " " + job.get("title", "")).lower()

    # Skill match (0-50 points)
    if user_skills:
        matched = sum(1 for s in user_skills if s in jd)
        skill_ratio = matched / max(len(user_skills), 1)
        score += int(skill_ratio * 50)

    # Title/experience keyword match (0-30 points)
    if exp_keywords:
        matched = sum(1 for kw in exp_keywords if kw in jd)
        exp_ratio = min(matched / max(len(exp_keywords), 1), 1.0)
        score += int(exp_ratio * 30)

    # Summary relevance (0-20 points)
    if user_summary:
        summary_words = set(w for w in user_summary.split() if len(w) > 4)
        if summary_words:
            matched = sum(1 for w in summary_words if w in jd)
            sum_ratio = min(matched / max(len(summary_words), 1), 1.0)
            score += int(sum_ratio * 20)

    return min(score, 100)
