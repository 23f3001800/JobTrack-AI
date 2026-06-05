from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import requests
import anthropic
from dotenv import load_dotenv

load_dotenv()


def fetch_with_requests(url: str) -> str:
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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        page.goto(
            url,
            wait_until="networkidle",
            timeout=30000,
        )

        html = page.content()

        browser.close()

        return html


def clean_html(html: str) -> str:
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


def scrape_job_url(url: str) -> str:
    """
    Extract structured job information from a URL.
    """

    try:
        html = fetch_with_requests(url)

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
            html = fetch_with_playwright(url)

    except Exception:
        html = fetch_with_playwright(url)

    raw_text = clean_html(html)

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