"""Playwright Auto-Fill — browser automation for job applications.

WHY Playwright over Selenium?
1. Async-native — works with our FastAPI async architecture
2. Auto-wait — no manual sleep() calls, elements are awaited
3. Built-in browser install (chromium via `playwright install`)
4. Better at handling modern SPAs (React-based job portals)

Supported portals:
- Greenhouse (boards.greenhouse.io)
- Lever (jobs.lever.co)
- Generic HTML forms (best-effort field matching)

Usage:
    from tools.autofill import auto_fill_application
    result = await auto_fill_application(
        job_url="https://boards.greenhouse.io/company/jobs/123",
        user_data={"name": "John Doe", "email": "john@example.com", ...}
    )
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


async def auto_fill_application(
    job_url: str,
    user_data: dict,
    resume_path: Optional[str] = None,
    headless: bool = True,
    timeout_ms: int = 30000,
) -> dict:
    """Auto-fill a job application form using Playwright.

    Args:
        job_url: URL of the job application page
        user_data: Dict with keys: name, email, phone, linkedin, cover_letter
        resume_path: Path to resume PDF file
        headless: Run browser without UI (True for server, False for debugging)
        timeout_ms: Max time to wait for page elements (ms)

    Returns:
        Dict with status, fields_filled, screenshot_path, and any errors
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "status": "error",
            "message": "Playwright not installed. Run: pip install playwright && playwright install chromium",
        }

    result = {
        "status": "pending",
        "url": job_url,
        "fields_filled": [],
        "fields_skipped": [],
        "screenshot_path": None,
        "submitted": False,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            # Navigate to the application page
            await page.goto(job_url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(2000)  # Let JS render

            # Detect portal type
            portal = _detect_portal(job_url, await page.content())

            # Fill fields based on portal type
            if portal == "greenhouse":
                result = await _fill_greenhouse(page, user_data, resume_path, result)
            elif portal == "lever":
                result = await _fill_lever(page, user_data, resume_path, result)
            else:
                result = await _fill_generic(page, user_data, resume_path, result)

            # Take screenshot for verification
            workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
            workspace.mkdir(parents=True, exist_ok=True)
            screenshot_path = str(workspace / "autofill_screenshot.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            result["screenshot_path"] = screenshot_path
            result["status"] = "filled"

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)

        finally:
            await browser.close()

    return result


def _detect_portal(url: str, html: str) -> str:
    """Detect which job portal we're on."""
    url_lower = url.lower()
    if "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower:
        return "greenhouse"
    if "lever.co" in url_lower or "jobs.lever" in url_lower:
        return "lever"
    if "workday" in url_lower:
        return "workday"
    # Check HTML content for portal signatures
    if "greenhouse" in html.lower():
        return "greenhouse"
    if "lever" in html.lower():
        return "lever"
    return "generic"


async def _fill_field(page, selectors: list, value: str, field_name: str, result: dict):
    """Try multiple selectors to fill a field."""
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if await element.is_visible(timeout=2000):
                await element.fill(value)
                result["fields_filled"].append(field_name)
                return True
        except Exception:
            continue
    result["fields_skipped"].append(field_name)
    return False


async def _upload_file(page, selectors: list, file_path: str, field_name: str, result: dict):
    """Try multiple selectors to upload a file."""
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if await element.count() > 0:
                await element.set_input_files(file_path)
                result["fields_filled"].append(field_name)
                return True
        except Exception:
            continue
    result["fields_skipped"].append(field_name)
    return False


async def _fill_greenhouse(page, user_data: dict, resume_path: Optional[str], result: dict) -> dict:
    """Fill Greenhouse application form.

    Greenhouse forms have predictable field IDs:
    #first_name, #last_name, #email, #phone, #resume
    """
    name_parts = user_data.get("name", "").split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Name fields
    await _fill_field(page, [
        "#first_name", "input[name='first_name']",
        "input[autocomplete='given-name']",
    ], first_name, "first_name", result)

    await _fill_field(page, [
        "#last_name", "input[name='last_name']",
        "input[autocomplete='family-name']",
    ], last_name, "last_name", result)

    # Email
    await _fill_field(page, [
        "#email", "input[name='email']",
        "input[type='email']",
    ], user_data.get("email", ""), "email", result)

    # Phone
    await _fill_field(page, [
        "#phone", "input[name='phone']",
        "input[type='tel']",
    ], user_data.get("phone", ""), "phone", result)

    # LinkedIn
    if user_data.get("linkedin"):
        await _fill_field(page, [
            "input[name*='linkedin']", "input[name*='LinkedIn']",
            "input[placeholder*='linkedin']",
        ], user_data["linkedin"], "linkedin", result)

    # Cover letter
    if user_data.get("cover_letter"):
        await _fill_field(page, [
            "textarea[name*='cover']", "#cover_letter",
            "textarea[placeholder*='cover']",
        ], user_data["cover_letter"], "cover_letter", result)

    # Resume upload
    if resume_path and os.path.exists(resume_path):
        await _upload_file(page, [
            "input[type='file']", "#resume",
            "input[name*='resume']",
        ], resume_path, "resume", result)

    result["portal"] = "greenhouse"
    return result


async def _fill_lever(page, user_data: dict, resume_path: Optional[str], result: dict) -> dict:
    """Fill Lever application form.

    Lever uses class-based selectors:
    .application-name, .application-email, etc.
    """
    name = user_data.get("name", "")

    # Name
    await _fill_field(page, [
        "input[name='name']", ".application-name input",
        "input[placeholder*='name' i]",
    ], name, "name", result)

    # Email
    await _fill_field(page, [
        "input[name='email']", ".application-email input",
        "input[type='email']",
    ], user_data.get("email", ""), "email", result)

    # Phone
    await _fill_field(page, [
        "input[name='phone']", ".application-phone input",
        "input[type='tel']",
    ], user_data.get("phone", ""), "phone", result)

    # LinkedIn / URLs
    if user_data.get("linkedin"):
        await _fill_field(page, [
            "input[name='urls[LinkedIn]']",
            "input[placeholder*='linkedin' i]",
            "input[name*='linkedin' i]",
        ], user_data["linkedin"], "linkedin", result)

    # Cover letter
    if user_data.get("cover_letter"):
        await _fill_field(page, [
            "textarea[name='comments']",
            "textarea[placeholder*='cover' i]",
            "textarea.application-additional",
        ], user_data["cover_letter"], "cover_letter", result)

    # Resume upload
    if resume_path and os.path.exists(resume_path):
        await _upload_file(page, [
            "input[type='file']",
            "input[name='resume']",
        ], resume_path, "resume", result)

    result["portal"] = "lever"
    return result


async def _fill_generic(page, user_data: dict, resume_path: Optional[str], result: dict) -> dict:
    """Best-effort fill for unknown job portals.

    Uses common HTML patterns: input[type=email], input[type=tel],
    label text matching, and placeholder text matching.
    """
    name = user_data.get("name", "")
    email = user_data.get("email", "")
    phone = user_data.get("phone", "")

    # Name — try various common selectors
    await _fill_field(page, [
        "input[name*='name' i]", "input[placeholder*='name' i]",
        "input[autocomplete='name']",
        "input[id*='name' i]",
    ], name, "name", result)

    # Email
    await _fill_field(page, [
        "input[type='email']", "input[name*='email' i]",
        "input[placeholder*='email' i]",
        "input[autocomplete='email']",
    ], email, "email", result)

    # Phone
    await _fill_field(page, [
        "input[type='tel']", "input[name*='phone' i]",
        "input[placeholder*='phone' i]",
        "input[autocomplete='tel']",
    ], phone, "phone", result)

    # Cover letter / message
    if user_data.get("cover_letter"):
        await _fill_field(page, [
            "textarea[name*='cover' i]", "textarea[name*='message' i]",
            "textarea[placeholder*='cover' i]",
            "textarea", # Last resort: first textarea on page
        ], user_data["cover_letter"], "cover_letter", result)

    # Resume upload
    if resume_path and os.path.exists(resume_path):
        await _upload_file(page, [
            "input[type='file']",
        ], resume_path, "resume", result)

    result["portal"] = "generic"
    return result
