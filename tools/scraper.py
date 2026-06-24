"""Job URL scraper — extract structured job details from a posting URL.

Architecture:
    1. Try requests (fast, 20s timeout)
    2. Fall back to Playwright (JS-rendered pages, 30s timeout)
    3. Validate content (not a captcha/login wall)
    4. Extract with Claude Haiku (structured fields)

WHY a separate scraper from job_search.py?
job_search.py handles DISCOVERY (find jobs from a query).
This module handles EXTRACTION (get full details from a known URL).
Different inputs, outputs, and failure modes.
"""
from bs4 import BeautifulSoup
import requests
import anthropic
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("autoapply.scraper")


def fetch_with_requests(url: str) -> str:
    """Fetch HTML via simple HTTP GET.

    WHY try requests first? It's 10x faster than Playwright
    and works for most static career pages (Greenhouse, Lever, etc.)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20,
    )

    response.raise_for_status()

    return response.text


def fetch_with_playwright(url: str) -> str:
    """Fetch HTML via headless Chromium (handles JS-rendered pages).

    WHY a context manager? The previous implementation could leak
    browser processes if page.goto() timed out before browser.close().
    Using 'with' ensures cleanup even on exceptions.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(
                url,
                wait_until="networkidle",
                timeout=30000,
            )
            html = page.content()
            return html
        finally:
            browser.close()


def clean_html(html: str) -> str:
    """Strip non-content HTML and extract text.

    WHY strip nav/footer/header? These contain menu items, copyright,
    and other noise that wastes LLM tokens and confuses extraction.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "noscript",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        separator="\n",
        strip=True,
    )

    return text[:8000]


def validate_job_content(text: str) -> tuple[bool, str]:
    """Check if scraped text is actually a job posting.

    Returns (is_valid, reason).

    WHY validate? Anti-bot sites return captcha pages, login walls,
    or 404s that look like HTML. Without validation, the pipeline
    generates cover letters for "Please verify you're human".
    """
    text_lower = text.lower()

    # Red flags — content is NOT a job posting
    red_flags = [
        "captcha",
        "verify you're human",
        "verify you are human",
        "please enable cookies",
        "access denied",
        "403 forbidden",
        "page not found",
        "404",
        "sign in to continue",
        "log in to view",
        "create an account",
        "unusual traffic",
    ]

    for flag in red_flags:
        if flag in text_lower:
            return False, f"Anti-bot or error page detected: '{flag}'"

    # Must have some job-related content
    job_indicators = [
        "requirements", "responsibilities", "qualifications",
        "apply", "experience", "skills", "salary", "role",
        "position", "job description", "we are looking",
        "you will", "what you'll do", "about the role",
    ]

    matches = sum(1 for ind in job_indicators if ind in text_lower)
    if matches < 2:
        return False, f"Content doesn't look like a job posting (only {matches} job indicators found)"

    if len(text.strip()) < 100:
        return False, "Content too short to be a job posting"

    return True, "OK"


def scrape_job_url(url: str) -> str:
    """Extract structured job information from a URL.

    Fallback chain:
    1. requests (fast) → 2. Playwright (JS) → 3. validate content → 4. LLM extract

    If content validation fails, returns a structured error message
    that tells the pipeline to use pre-fetched data or ask the user.
    """
    html = None

    # Step 1: Try fast HTTP request
    try:
        html = fetch_with_requests(url)

        # Check if page needs JavaScript rendering
        javascript_indicators = [
            "enable javascript",
            "you need to enable javascript",
            "__next",
            "react-root",
        ]

        if any(
            indicator in html.lower()
            for indicator in javascript_indicators
        ):
            logger.info("Page requires JS rendering, using Playwright: %s", url)
            html = fetch_with_playwright(url)

    except Exception as e:
        logger.warning("requests failed for %s: %s, trying Playwright", url, e)
        try:
            html = fetch_with_playwright(url)
        except Exception as pw_err:
            logger.error("Both requests and Playwright failed for %s: %s", url, pw_err)
            return (
                f"SCRAPING FAILED: Could not access {url}\n"
                f"Error: {pw_err}\n\n"
                "This URL may have anti-bot protection (Glassdoor, LinkedIn).\n"
                "The job description should be provided manually or via search API."
            )

    # Step 2: Clean HTML to text
    raw_text = clean_html(html)

    # Step 3: Validate content
    is_valid, reason = validate_job_content(raw_text)
    if not is_valid:
        logger.warning("Content validation failed for %s: %s", url, reason)
        return (
            f"SCRAPING FAILED: {reason}\n"
            f"URL: {url}\n\n"
            "The page returned blocked/invalid content.\n"
            "The job description should be provided manually or via search API."
        )

    # Step 4: Extract structured data with Claude
    try:
        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[
                {
                    "role": "user",
                    "content": f"""
Extract the following fields.

Return plain text only.

JOB TITLE:
COMPANY:
LOCATION:
EMPLOYMENT TYPE:
SALARY:

KEY REQUIREMENTS:
- bullet points

RESPONSIBILITIES:
- bullet points

TECH STACK:
- bullet points

COMPANY DESCRIPTION:
1-2 sentences

JOB POSTING:

{raw_text}
""",
                }
            ],
        )

        return response.content[0].text
    except Exception as e:
        logger.error("LLM extraction failed for %s: %s", url, e)
        # Return raw text as fallback — better than nothing
        return f"JOB POSTING (raw text, LLM extraction failed):\n\n{raw_text[:4000]}"