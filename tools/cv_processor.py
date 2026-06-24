import os
from pypdf import PdfReader
import anthropic
from dotenv import load_dotenv
load_dotenv()


def load_cv(path: str = None, cv_text: str = None) -> str:
    """Extract text from PDF CV or use pre-extracted text.

    WHY accept cv_text directly?
    In multi-user mode, each user's CV text is stored in the database
    (extracted during upload). Passing it directly avoids filesystem
    dependency and supports concurrent users with different CVs.

    Fallback order:
    1. cv_text parameter (from database)
    2. PDF file at path parameter
    3. PDF file at CV_PATH env var
    """
    # Prefer pre-extracted text from database
    if cv_text and cv_text.strip():
        return cv_text.strip()

    # Fall back to file-based extraction
    path = path or os.getenv("CV_PATH", "./my_cv.pdf")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"CV not found at {path}. Upload your resume in Settings or set CV_PATH in .env"
        )
    reader = PdfReader(path)
    # WHY join all pages?
    # A CV spans multiple pages. We need the full text
    # to understand the candidate's complete experience.
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text.strip()

def tailor_cv_bullets(job_requirements: str, company_profile: str,
                      cv_text: str = None) -> str:
    """
    Rewrite CV bullets to match job requirements.
    Uses Claude Sonnet — quality matters here most.
    """
    cv_content = load_cv(cv_text=cv_text)
    client = anthropic.Anthropic()

    # WHY this specific prompt structure?
    # We give Claude 3 inputs in order of priority:
    # 1. Job requirements (most important — what they're hiring for)
    # 2. Company profile (context for tone and specificity)
    # 3. The raw CV (source material to rewrite from)
    # Putting requirements FIRST biases Claude toward matching them.
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role":"user","content":
            f"""You are a professional CV coach. Rewrite 4-6 bullet points from this candidate's experience to match the job requirements.

Rules:
- Use the STAR format (Situation, Task, Action, Result) where possible
- Include specific numbers and metrics if present in the original CV
- Mirror the language from the job requirements (keywords matter for ATS)
- Reference the company's tech stack when the candidate has relevant experience
- Do NOT invent experience the candidate doesn't have
- Output ONLY the tailored bullet points, nothing else

JOB REQUIREMENTS:
{job_requirements}

COMPANY PROFILE:
{company_profile}

CANDIDATE'S FULL CV:
{cv_content[:3000]}"""}]
    )
    return resp.content[0].text


def write_cover_letter(job_analysis: str, company_profile: str,
                       tailored_bullets: str, cv_text: str = None) -> str:
    """Write a personalised 3-paragraph cover letter."""
    cv_content = load_cv(cv_text=cv_text)
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,
        messages=[{"role":"user","content":
            f"""Write a professional 3-paragraph cover letter.

Para 1: Why THIS company specifically (use company profile details — not generic)
Para 2: What I bring to THIS role (use tailored bullets AND my CV as evidence)
Para 3: Forward-looking — what I'd work on / contribute

Must include at least one specific detail from the company profile.
Must NOT start with "I am writing to apply for..."
Keep under 300 words. No fluff.

JOB: {job_analysis[:500]}
COMPANY: {company_profile[:400]}
MY RELEVANT EXPERIENCE (tailored): {tailored_bullets}
MY FULL CV: {cv_content[:2000]}"""}]
    )
    return resp.content[0].text