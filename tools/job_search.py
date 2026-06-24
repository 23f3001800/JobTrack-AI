"""Multi-provider job search — SerpAPI Google Jobs + Himalayas API.

WHY two providers instead of one?
- SerpAPI ($0): 250 free searches/month, covers ALL platforms (LinkedIn, Indeed,
  Glassdoor, Naukri, Greenhouse, Lever, Workday, etc.), returns full JDs.
- Himalayas (free, no key): Unlimited searches, but remote jobs only.

Users pick their preferred provider in the UI. The system auto-falls back
to Himalayas if SerpAPI key is missing or exhausted.
"""
import os
import logging
from typing import Optional

import requests as http_requests

logger = logging.getLogger("autoapply.job_search")


# ───────────────────────────────────────────
# Provider: SerpAPI Google Jobs
# ───────────────────────────────────────────

def search_serpapi(
    query: str,
    location: str = "",
    max_results: int = 20,
    api_key: Optional[str] = None,
) -> list[dict]:
    """Search Google Jobs via SerpAPI.

    Returns structured job listings with full descriptions,
    direct apply URLs, and platform detection.

    WHY SerpAPI instead of scraping Google directly?
    Google Jobs aggregates from LinkedIn, Indeed, Glassdoor, Greenhouse,
    Lever, Workday, etc. into one search. SerpAPI provides a clean JSON
    API for this. 250 free searches/month is plenty for personal use.
    """
    key = api_key or os.getenv("SERPAPI_KEY", "")
    if not key:
        logger.warning("SERPAPI_KEY not set — cannot use SerpAPI provider")
        return []

    params = {
        "engine": "google_jobs",
        "q": query,
        "api_key": key,
        "hl": "en",
        "num": min(max_results, 20),  # Google Jobs max per page
    }
    if location:
        params["location"] = location

    try:
        resp = http_requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for item in data.get("jobs_results", []):
            # Extract the best apply link
            apply_links = item.get("apply_options", [])
            apply_url = ""
            source = "web"
            if apply_links:
                # Prefer the first direct apply link
                best = apply_links[0]
                apply_url = best.get("link", "")
                source = _detect_source(apply_url)

            jobs.append({
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("location", ""),
                "description": item.get("description", ""),
                "url": apply_url or item.get("share_link", ""),
                "source": source,
                "posted": item.get("detected_extensions", {}).get("posted_at", ""),
                "salary": item.get("detected_extensions", {}).get("salary", ""),
                "schedule": item.get("detected_extensions", {}).get("schedule_type", ""),
                "provider": "serpapi",
                "job_id": item.get("job_id", ""),
                "apply_options": [
                    {"title": opt.get("title", ""), "url": opt.get("link", "")}
                    for opt in apply_links[:3]
                ],
            })

        logger.info("SerpAPI returned %d jobs for query: %s", len(jobs), query)
        return jobs

    except Exception as e:
        logger.error("SerpAPI search failed: %s", e)
        return []


# ───────────────────────────────────────────
# Provider: Himalayas (Free, no API key)
# ───────────────────────────────────────────

def search_himalayas(
    query: str,
    location: str = "",
    max_results: int = 20,
) -> list[dict]:
    """Search Himalayas.app for remote job listings.

    WHY Himalayas? Free, no API key, no rate limits (within reason),
    and returns structured job data including full descriptions.
    Limitation: remote jobs only.
    """
    params = {
        "q": query,
        "limit": min(max_results, 50),
    }
    # Himalayas doesn't have a location filter per se (all remote),
    # but we include it in the query for better relevance
    if location and location.lower() != "remote":
        params["q"] = f"{query} {location}"

    try:
        resp = http_requests.get(
            "https://himalayas.app/jobs/api/search",
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for item in data.get("jobs", []):
            jobs.append({
                "title": item.get("title", ""),
                "company": item.get("companyName", item.get("company", "")),
                "location": item.get("location", "Remote"),
                "description": item.get("description", ""),
                "url": item.get("applicationLink", item.get("url", "")),
                "source": "himalayas",
                "posted": item.get("pubDate", item.get("postedAt", "")),
                "salary": _format_salary(item),
                "schedule": item.get("type", ""),
                "provider": "himalayas",
                "job_id": str(item.get("id", "")),
                "apply_options": [],
                "seniority": item.get("seniority", ""),
                "categories": item.get("categories", []),
            })

        logger.info("Himalayas returned %d jobs for query: %s", len(jobs), query)
        return jobs

    except Exception as e:
        logger.error("Himalayas search failed: %s", e)
        return []


# ───────────────────────────────────────────
# Unified search interface
# ───────────────────────────────────────────

def search_jobs(
    query: str,
    provider: str = "auto",
    location: str = "",
    max_results: int = 20,
    serpapi_key: Optional[str] = None,
) -> list[dict]:
    """Search for jobs using the specified provider.

    Args:
        query: Job search query (e.g. "AI Engineer Python")
        provider: "serpapi", "himalayas", or "auto"
        location: Optional location filter
        max_results: Max number of results (1-25)
        serpapi_key: Optional SerpAPI key (overrides env var)

    Returns:
        List of job dicts with title, company, location, description, url, etc.

    WHY a unified interface?
    The frontend and batch pipeline shouldn't care which provider is used.
    This function handles provider selection and fallback logic.
    """
    max_results = max(1, min(max_results, 25))

    if provider == "serpapi":
        results = search_serpapi(query, location, max_results, serpapi_key)
        if not results:
            logger.info("SerpAPI returned no results, falling back to Himalayas")
            results = search_himalayas(query, location, max_results)
        return results

    if provider == "himalayas":
        return search_himalayas(query, location, max_results)

    # Auto mode: try SerpAPI first if key available, else Himalayas
    if os.getenv("SERPAPI_KEY") or serpapi_key:
        results = search_serpapi(query, location, max_results, serpapi_key)
        if results:
            return results

    return search_himalayas(query, location, max_results)


def get_available_providers() -> list[dict]:
    """Return list of available job search providers and their status."""
    providers = []

    has_serpapi = bool(os.getenv("SERPAPI_KEY"))
    providers.append({
        "id": "serpapi",
        "name": "SerpAPI (Google Jobs)",
        "description": "All platforms: LinkedIn, Indeed, Glassdoor, Naukri, Greenhouse, Lever, Workday...",
        "available": has_serpapi,
        "note": "" if has_serpapi else "Add SERPAPI_KEY to .env (free: 250 searches/month)",
        "coverage": "all",
    })

    providers.append({
        "id": "himalayas",
        "name": "Himalayas (Free)",
        "description": "Remote jobs worldwide — no API key needed",
        "available": True,
        "note": "Remote jobs only",
        "coverage": "remote",
    })

    return providers


# ───────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────

def _detect_source(url: str) -> str:
    """Detect the job platform from a URL."""
    url_lower = url.lower()
    platforms = {
        "linkedin.com": "linkedin",
        "indeed.com": "indeed",
        "glassdoor.com": "glassdoor",
        "glassdoor.co": "glassdoor",
        "lever.co": "lever",
        "greenhouse.io": "greenhouse",
        "boards.greenhouse": "greenhouse",
        "wellfound.com": "wellfound",
        "angel.co": "wellfound",
        "workday.com": "workday",
        "myworkdayjobs.com": "workday",
        "smartrecruiters.com": "smartrecruiters",
        "taleo.net": "taleo",
        "ashbyhq.com": "ashby",
        "naukri.com": "naukri",
        "jobs.lever.co": "lever",
    }
    for domain, platform in platforms.items():
        if domain in url_lower:
            return platform
    return "web"


def _format_salary(item: dict) -> str:
    """Format salary from Himalayas job data."""
    min_sal = item.get("minSalary") or item.get("salaryMin")
    max_sal = item.get("maxSalary") or item.get("salaryMax")
    currency = item.get("salaryCurrency", "USD")

    if min_sal and max_sal:
        return f"{currency} {min_sal:,}–{max_sal:,}"
    if min_sal:
        return f"{currency} {min_sal:,}+"
    return ""
