"""Structured resume parser — extracts profile data from resume text.

WHY use an LLM instead of regex?
Resume formats vary wildly — multi-column layouts, creative headings,
non-standard section names. An LLM handles all of these reliably
while a regex parser would need hundreds of rules and still fail
on unconventional resumes.

Uses Claude Haiku for cost efficiency — resume parsing is a simple
extraction task that doesn't need Sonnet-level reasoning.
"""
import json
import os

from dotenv import load_dotenv

load_dotenv()

# Schema for the structured profile output
PARSED_PROFILE_SCHEMA = {
    "full_name": "string",
    "email": "string",
    "phone": "string",
    "linkedin_url": "string",
    "github_url": "string",
    "summary": "string (professional summary, 2-3 sentences)",
    "skills": ["list of skill strings"],
    "experience": [
        {
            "title": "job title",
            "company": "company name",
            "start_date": "start date",
            "end_date": "end date or 'Present'",
            "bullets": ["achievement/responsibility bullet points"],
        }
    ],
    "education": [
        {
            "degree": "degree name",
            "institution": "school/university name",
            "year": "graduation year or date range",
            "details": "GPA, honors, relevant coursework (optional)",
        }
    ],
    "projects": [
        {
            "name": "project name",
            "description": "brief description",
            "technologies": ["tech used"],
        }
    ],
    "certifications": ["certification name and issuer"],
    "achievements": ["notable achievement or award"],
}

PARSE_PROMPT = """You are a resume parser. Extract structured information from the following resume text.

Return a JSON object matching this exact schema:
{schema}

Rules:
- Extract ALL information present in the resume. Do not invent or hallucinate data.
- If a field is not found in the resume, use an empty string "" for strings or [] for arrays.
- For experience: list entries in reverse chronological order (most recent first).
- For skills: extract individual skills as separate items, not groups.
- For phone: include country code if present.
- For URLs: extract full URLs, or construct from usernames (e.g., linkedin.com/in/username).
- For summary: if no explicit summary section exists, generate a brief 2-sentence professional summary from the resume content.

Resume text:
---
{cv_text}
---

Return ONLY valid JSON. No markdown, no explanation, no code blocks."""


def parse_resume(cv_text: str) -> dict:
    """Parse resume text into structured profile data using Claude.

    Args:
        cv_text: Raw text extracted from a resume PDF.

    Returns:
        Dict with structured profile fields (name, skills, experience, etc.)
        Returns a minimal stub if parsing fails.
    """
    if not cv_text or not cv_text.strip():
        return _empty_profile()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # No API key — use regex fallback
        return _extract_profile_regex(cv_text)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": PARSE_PROMPT.format(
                        schema=json.dumps(PARSED_PROFILE_SCHEMA, indent=2),
                        cv_text=cv_text[:8000],  # Limit to avoid token overflow
                    ),
                }
            ],
        )

        raw = response.content[0].text.strip()

        # Handle markdown-wrapped JSON
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]  # Remove opening ```json
            raw = raw.rsplit("```", 1)[0]  # Remove closing ```

        parsed = json.loads(raw)
        return _validate_profile(parsed)

    except Exception as e:
        # Fallback: extract what we can with regex
        profile = _extract_profile_regex(cv_text)
        if not profile.get("summary"):
            profile["summary"] = f"AI parsing unavailable ({type(e).__name__}). Profile extracted via pattern matching."
        return profile


def _empty_profile() -> dict:
    """Return an empty profile structure."""
    return {
        "full_name": "",
        "email": "",
        "phone": "",
        "linkedin_url": "",
        "github_url": "",
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "achievements": [],
    }


def _validate_profile(data: dict) -> dict:
    """Ensure all expected fields exist with correct types."""
    base = _empty_profile()
    for key, default in base.items():
        if key not in data:
            data[key] = default
        elif isinstance(default, list) and not isinstance(data[key], list):
            data[key] = default
        elif isinstance(default, str) and not isinstance(data[key], str):
            data[key] = str(data[key]) if data[key] else ""
    return data


def _extract_profile_regex(cv_text: str) -> dict:
    """Extract profile data from resume text using regex patterns.

    WHY a full regex fallback? If the Claude API is unavailable (wrong model,
    rate limited, no key), users still need their name/email/phone populated
    in the onboarding form. Pattern matching handles 80%+ of standard resumes.
    """
    import re

    profile = _empty_profile()

    # ── Email ──
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', cv_text)
    if email_match:
        profile["email"] = email_match.group(0)

    # ── Phone ──
    phone_match = re.search(
        r'(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}',
        cv_text
    )
    if phone_match:
        profile["phone"] = phone_match.group(0).strip()

    # ── LinkedIn ──
    linkedin_match = re.search(
        r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+',
        cv_text, re.IGNORECASE
    )
    if linkedin_match:
        url = linkedin_match.group(0)
        if not url.startswith("http"):
            url = "https://" + url
        profile["linkedin_url"] = url

    # ── GitHub ──
    github_match = re.search(
        r'(?:https?://)?(?:www\.)?github\.com/[\w-]+',
        cv_text, re.IGNORECASE
    )
    if github_match:
        url = github_match.group(0)
        if not url.startswith("http"):
            url = "https://" + url
        profile["github_url"] = url

    # ── Full Name ──
    # Strategy: PDFs often split "VIKAS" and "RAJPUT" on separate lines.
    # First try joining consecutive short alpha-only lines at the top.
    # Fall back to single-line match if that doesn't work.
    lines = [l.strip() for l in cv_text.split("\n") if l.strip()]

    # Strategy 1: Join consecutive short name-like tokens
    name_parts = []
    for line in lines[:8]:
        clean = line.strip()
        if clean == "|" or not clean:
            continue
        if re.search(r'@|http|linkedin|github|PROFILE|SUMMARY|EXPERIENCE|\d{5,}', clean, re.IGNORECASE):
            break
        # Pure alphabetic token (possibly with dots/hyphens for initials)
        if len(clean) <= 30 and re.match(r'^[A-Za-z\s.\'-]+$', clean):
            name_parts.append(clean)
        else:
            break
        if len(name_parts) >= 3:
            break
    if name_parts:
        profile["full_name"] = " ".join(name_parts)

    # Strategy 2: If no name found, try single longer lines
    if not profile["full_name"]:
        for line in lines[:5]:
            if re.search(r'@|http|linkedin|github|\d{5,}|PROFILE|SUMMARY|EXPERIENCE|EDUCATION|SKILLS|OBJECTIVE', line, re.IGNORECASE):
                continue
            clean = re.sub(r'\s*\|\s*', ' ', line).strip()
            clean = re.sub(r'[•·|]', ' ', clean).strip()
            clean = re.sub(r'\s+', ' ', clean)
            if 2 < len(clean) < 50 and not re.search(r'\d{4}', clean):
                profile["full_name"] = clean
                break

    # ── Summary / Profile ──
    summary_match = re.search(
        r'(?:PROFILE|SUMMARY|ABOUT|OBJECTIVE)\s*\n+(.*?)(?:\n\s*\n|\n[A-Z]{3,})',
        cv_text, re.IGNORECASE | re.DOTALL
    )
    if summary_match:
        profile["summary"] = summary_match.group(1).strip()[:500]

    # ── Skills ──
    profile["skills"] = _extract_skills_basic(cv_text)

    # ── Education ──
    edu_section = re.search(
        r'EDUCATION\s*\n+(.*?)(?:\n\s*\n\s*[A-Z]{3,}|\Z)',
        cv_text, re.IGNORECASE | re.DOTALL
    )
    if edu_section:
        edu_text = edu_section.group(1)
        # Try to find degree lines
        degree_matches = re.findall(
            r'((?:B\.?S\.?|M\.?S\.?|B\.?Tech|M\.?Tech|B\.?A\.?|M\.?A\.?|Ph\.?D|MBA|Bachelor|Master|Doctor)[\w\s,.-]*)',
            edu_text, re.IGNORECASE
        )
        for deg in degree_matches[:3]:
            profile["education"].append({
                "degree": deg.strip(),
                "institution": "",
                "year": "",
                "details": "",
            })

    return profile


def _extract_skills_basic(cv_text: str) -> list[str]:
    """Basic keyword extraction for skills when LLM is unavailable.

    WHY a fallback? If the user doesn't have an Anthropic API key
    (local dev, testing), we still want some skill extraction.
    """
    common_skills = [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go",
        "Rust", "Ruby", "PHP", "Swift", "Kotlin", "React", "Vue", "Angular",
        "Node.js", "Django", "Flask", "FastAPI", "Spring", "Docker",
        "Kubernetes", "AWS", "GCP", "Azure", "PostgreSQL", "MySQL",
        "MongoDB", "Redis", "GraphQL", "REST", "Git", "Linux", "SQL",
        "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning",
        "NLP", "Computer Vision", "Data Science", "Data Engineering",
        "DevOps", "CI/CD", "Agile", "Scrum", "Figma", "HTML", "CSS",
    ]
    text_upper = cv_text.upper()
    return [s for s in common_skills if s.upper() in text_upper]

