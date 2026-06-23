"""Follow-up Generator — creates polite follow-up messages after applying.

WHY a follow-up tool?
Studies show a well-timed follow-up increases response rates by 30%.
Most candidates don't follow up because they don't know what to write.
This tool generates context-aware follow-ups based on:
- How long since the application was submitted
- The company and role details
- The original cover letter tone

Usage:
    from tools.followup import generate_followup
    msg = generate_followup(company, job_title, days_since_applied)
"""
import anthropic
from dotenv import load_dotenv

load_dotenv()


def generate_followup(
    company: str,
    job_title: str,
    days_since_applied: int = 7,
    cover_letter_excerpt: str = "",
    channel: str = "email",
) -> dict:
    """Generate a follow-up message for a job application.

    Args:
        company: Company name
        job_title: Job title applied for
        days_since_applied: Days since application was submitted
        cover_letter_excerpt: First paragraph of original cover letter
        channel: "email" or "linkedin"

    Returns:
        Dict with: subject (for email), message, tone_notes
    """
    channel_guidance = {
        "email": "Write a professional email. Include a subject line.",
        "linkedin": "Write a short LinkedIn message (max 300 chars). "
                    "Be casual but professional. No subject line needed.",
    }

    prompt = f"""Generate a follow-up message for a job application.

Company: {company}
Position: {job_title}
Days since applied: {days_since_applied}
Channel: {channel}
Original cover letter excerpt: {cover_letter_excerpt or "Not available"}

{channel_guidance.get(channel, channel_guidance["email"])}

Rules:
- Be concise and respectful of their time
- Reference the specific role
- Show continued enthusiasm without desperation
- If >14 days, acknowledge the delay gracefully
- NO "I hope this finds you well" or similar filler
- NO "I'm just checking in" — add value instead

Return as JSON:
{{
    "subject": "<email subject line or empty for linkedin>",
    "message": "<the follow-up message>",
    "tone_notes": "<1-sentence note on the tone used>"
}}"""

    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    raw = response.content[0].text.strip()

    # Handle markdown-wrapped JSON
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "subject": f"Follow-up: {job_title} application",
            "message": raw,
            "tone_notes": "Auto-generated fallback",
        }
