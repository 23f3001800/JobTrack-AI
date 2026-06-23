"""Interview Prep Generator — creates likely interview questions per job.

WHY an interview prep tool?
After applying, the next step is the interview. This tool generates
tailored questions based on the job requirements, company profile,
and the candidate's background. It saves prep time and increases
confidence.

Three question categories:
1. Technical — based on the job's tech stack requirements
2. Behavioral — STAR-format prompts based on the role
3. Company-specific — based on the company research

Usage:
    from tools.interview_prep import generate_interview_prep
    prep = generate_interview_prep(job_analysis, company_profile)
"""
import anthropic
from dotenv import load_dotenv

load_dotenv()


def generate_interview_prep(
    job_analysis: str,
    company_profile: str = "",
    role_fit: str = "",
    num_questions: int = 5,
) -> str:
    """Generate tailored interview questions and talking points.

    Args:
        job_analysis: Scraped job posting analysis
        company_profile: Company research data
        role_fit: Role fit analysis (optional)
        num_questions: Questions per category (default 5)

    Returns:
        Formatted markdown string with questions and prep notes.

    WHY use Claude Haiku instead of Sonnet?
    Interview questions are structured and pattern-based — they don't
    need the creative writing quality of Sonnet. Haiku is 10x cheaper
    and generates good questions reliably.
    """
    prompt = f"""Generate interview preparation for this role.

## Job Analysis
{job_analysis}

## Company Profile
{company_profile or "Not available"}

## Candidate Fit
{role_fit or "Not available"}

Generate {num_questions} questions for EACH category below.
For each question, include a brief "prep tip" on how to answer.

Format as markdown:

## 🔧 Technical Questions
1. **Question**: ...
   - *Prep tip*: ...

## 🎯 Behavioral Questions (STAR format)
1. **Question**: ...
   - *Prep tip*: ...

## 🏢 Company-Specific Questions
1. **Question**: ...
   - *Prep tip*: ...

## 💡 Questions to Ask the Interviewer
1. ...

Be specific to THIS role and company. No generic questions."""

    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
