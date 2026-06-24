"""Scout Agent — Job discovery and scraping.

Responsibility: Extract structured job information from URLs.
Future: Will also search across job platforms (Phase 8).

Model: Claude Haiku (fast, cheap — scraping is I/O bound)
Tools: scrape_job_url, (future: search_jobs, filter_and_rank)
"""
from tools.executor import execute_tool
from tools.schemas import TOOL_SCRAPE_JOB
from langsmith import traceable

# WHY a dedicated system prompt instead of sharing the orchestrator's?
# The scout needs to focus ONLY on extracting job data accurately.
# A shared prompt with all 9 tools confuses the LLM about what to do.
SCOUT_SYSTEM = """You are the Scout Agent in a job application system.
Your ONLY job: scrape the job URL and extract structured job details.
Call the scrape_job_url tool with the provided URL. Nothing else."""

SCOUT_TOOLS = [TOOL_SCRAPE_JOB]


@traceable(name="scout-agent", tags=["agent", "scout"])
def run_scout(state: dict) -> dict:
    """Scrape job URL and return job analysis.

    WHY use an LLM here instead of calling scrape_job_url directly?
    For now it's a thin wrapper. But in Phase 8, the scout will need
    to reason about search results, rank jobs, and decide which to
    scrape — that requires LLM reasoning. Building the agent
    structure now avoids a rewrite later.
    """
    # If job description was pre-fetched from search API, skip scraping
    pre_fetched = state.get("job_description_text", "")
    if pre_fetched:
        return {
            "job_analysis": pre_fetched,
            "messages": [{"agent": "scout", "content": "Using pre-fetched job description (no scraping needed)"}],
            "iterations": state.get("iterations", 0) + 1,
        }

    job_url = state["job_url"]

    # For URL mode, we can skip the LLM and call the tool directly.
    # This saves ~500 tokens per run ($0.001) while maintaining
    # the agent interface for future search mode.
    result = execute_tool("scrape_job_url", {"url": job_url})

    return {
        "job_analysis": result,
        "messages": [
            {
                "role": "assistant",
                "content": f"[Scout] Job scraped: {result[:100]}...",
            }
        ],
        "iterations": state.get("iterations", 0) + 1,
    }
