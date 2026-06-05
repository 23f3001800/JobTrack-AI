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