from ddgs import DDGS
import anthropic
from dotenv import load_dotenv

load_dotenv()


def research_company(company_name: str, job_title: str = "") -> str:
    """
    Build a company profile using web search + Claude.
    """

    client = anthropic.Anthropic()

    queries = [
        f"{company_name} engineering blog tech stack",
        f"{company_name} culture values mission",
        f"{company_name} recent news funding products 2025 2026",
    ]

    snippets = []

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = ddgs.text(query, max_results=3)

                for result in results:
                    snippets.append(
                        f"TITLE: {result.get('title', '')}\n"
                        f"SNIPPET: {result.get('body', '')}"
                    )

            except Exception as e:
                snippets.append(f"Search error: {e}")

    combined = "\n\n".join(snippets)[:6000]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": f"""
Based on these search results, summarize {company_name}
for a candidate applying to a {job_title} role.

Include:

1. What the company does
2. Products and customers
3. Tech stack and engineering culture
4. Company values
5. Recent news or notable developments
6. Why an engineer might want to work there

Keep under 300 words.

Search Results:

{combined}
""",
            }
        ],
    )

    return response.content[0].text


def analyze_role_fit(job_analysis: str, user_background: str) -> str:
    """Compare job requirements against the user's background to assess fit.

    WHY this exists: Before spending tokens on cover letters and CV
    tailoring, we should know HOW WELL the candidate fits. This helps:
    1. The Writer agent focus on strengths and address gaps
    2. The user decide if it's worth applying
    3. The cover letter reference specific alignment points

    Args:
        job_analysis: The scraped job analysis from step 1.
        user_background: The user's CV/background summary.

    Returns:
        A structured analysis: fit score, matching skills,
        gaps to address, and talking points for the cover letter.
    """
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content":
            f"""Analyze how well this candidate fits the job.

Provide:
1. FIT SCORE: X/10
2. MATCHING SKILLS: bullet list of skills that directly match
3. GAPS: skills the job requires that the candidate may lack
4. TALKING POINTS: 3 specific things to emphasise in the cover letter
5. HONEST ASSESSMENT: 1-2 sentences on overall fit

JOB REQUIREMENTS:
{job_analysis[:1000]}

CANDIDATE BACKGROUND:
{user_background[:1500]}"""}]
    )
    return resp.content[0].text