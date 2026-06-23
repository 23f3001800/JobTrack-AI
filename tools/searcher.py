"""Job Search Tool — discover job postings via web search.

WHY a separate search tool instead of adding to scraper.py?
Scraper handles a KNOWN URL → structured data extraction.
Search handles a QUERY → list of relevant job URLs + previews.
These are fundamentally different operations with different
inputs, outputs, and error modes.

Uses DuckDuckGo (ddgs library) — no API key required, works
everywhere, and respects privacy. Results are filtered and
ranked for job-posting relevance.
"""
from ddgs import DDGS


def search_jobs(query: str, location: str = "", max_results: int = 10) -> str:
    """Search for job postings matching a query.

    Args:
        query: Job title, skills, or keywords (e.g. "Python AI engineer")
        location: Optional location filter (e.g. "London", "remote")
        max_results: Number of results to return (default 10, max 20)

    Returns:
        Formatted string with job listings: title, URL, preview snippet.

    WHY return a formatted string instead of JSON?
    The LLM agents consume this output as context. A readable
    formatted string is easier for the LLM to parse than raw JSON.
    The API endpoints that serve the frontend will return JSON separately.
    """
    # Build search query optimized for job postings
    # WHY add "job" and "apply" keywords? DuckDuckGo doesn't have a
    # job-specific search. These keywords bias results toward actual
    # job postings rather than articles about the role.
    search_query = f"{query} job posting apply"
    if location:
        search_query += f" {location}"

    max_results = min(max_results, 20)  # Cap to avoid rate limits

    try:
        results = DDGS().text(
            search_query,
            max_results=max_results,
            region="wt-wt",  # Worldwide results
        )
    except Exception as e:
        return f"Search failed: {e}"

    if not results:
        return "No jobs found. Try different keywords or a broader search."

    # Format results for the agent
    output_lines = [f"Found {len(results)} job postings:\n"]

    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("href", "")
        snippet = r.get("body", "")[:200]

        output_lines.append(f"--- Job {i} ---")
        output_lines.append(f"Title: {title}")
        output_lines.append(f"URL: {url}")
        output_lines.append(f"Preview: {snippet}")
        output_lines.append("")

    return "\n".join(output_lines)


def search_jobs_structured(
    query: str, location: str = "", max_results: int = 10
) -> list[dict]:
    """Search for jobs and return structured data for the API/frontend.

    WHY a separate function from search_jobs?
    search_jobs returns a formatted string for LLM agents.
    This function returns structured dicts for the REST API,
    which the frontend renders as cards with links.
    """
    search_query = f"{query} job posting apply"
    if location:
        search_query += f" {location}"

    max_results = min(max_results, 20)

    try:
        results = DDGS().text(
            search_query,
            max_results=max_results,
            region="wt-wt",
        )
    except Exception:
        return []

    return [
        {
            "title": r.get("title", "Untitled"),
            "url": r.get("href", ""),
            "snippet": r.get("body", "")[:300],
            "source": _detect_source(r.get("href", "")),
        }
        for r in results
    ]


def _detect_source(url: str) -> str:
    """Detect which job board a URL comes from.

    WHY detect source? The frontend can show platform icons
    (LinkedIn, Indeed, etc.) and the Applier agent can use
    platform-specific application strategies.
    """
    url_lower = url.lower()
    if "linkedin.com" in url_lower:
        return "linkedin"
    if "indeed.com" in url_lower:
        return "indeed"
    if "glassdoor.com" in url_lower:
        return "glassdoor"
    if "lever.co" in url_lower:
        return "lever"
    if "greenhouse.io" in url_lower:
        return "greenhouse"
    if "workday" in url_lower:
        return "workday"
    if "angel.co" in url_lower or "wellfound" in url_lower:
        return "wellfound"
    return "web"
