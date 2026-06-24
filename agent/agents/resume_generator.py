"""Resume Generator agent — creates a tailored PDF resume per job.

WHY a separate agent node instead of inline in writer?
1. Separation of concerns — Writer generates text, this generates PDFs
2. The PDF needs the full parsed profile (experience, education, skills)
   which Writer doesn't use
3. Resume generation can be skipped or replaced independently
4. The PDF filename/path needs to be tracked in state for download

This node runs AFTER Writer (needs tailored_bullets) and BEFORE Quality
(quality agent can evaluate the resume).
"""


def run_resume_generator(state: dict) -> dict:
    """Generate a tailored PDF resume for the current job application.

    Reads from state:
        - tailored_bullets: Job-specific CV bullets from Writer
        - user_profile: Full parsed profile (experience, education, etc.)
        - job_analysis: Job requirements (used to extract title/company)
        - company_profile: Company info
        - role_fit: Role fit analysis

    Returns:
        - resume_pdf_path: Local file path to the generated PDF
        - resume_pdf_url: Download URL for the PDF
    """
    from tools.pdf_generator import generate_resume_pdf

    tailored_bullets = state.get("tailored_bullets", "")
    user_profile = state.get("user_profile", {})
    job_analysis = state.get("job_analysis", "")
    role_fit = state.get("role_fit", "")

    # Extract name and contact from user profile
    parsed = user_profile.get("parsed_profile", {})
    name = (
        user_profile.get("full_name")
        or parsed.get("full_name", "")
        or "Candidate"
    )
    email = (
        user_profile.get("email")
        or parsed.get("email", "")
    )
    phone = (
        user_profile.get("phone")
        or parsed.get("phone", "")
    )
    background = (
        user_profile.get("background")
        or parsed.get("summary", "")
    )
    linkedin = (
        user_profile.get("linkedin_url")
        or parsed.get("linkedin_url", "")
    )
    github = (
        user_profile.get("github_url")
        or parsed.get("github_url", "")
    )

    # Extract job title and company from job_analysis text
    job_title = _extract_field(job_analysis, "job_title", "Position")
    company = _extract_field(job_analysis, "company", "Company")

    if not tailored_bullets:
        return {
            "resume_pdf_path": "",
            "resume_pdf_url": "",
            "messages": [
                {"role": "system", "content": "resume_generator: skipped — no tailored bullets available"}
            ],
        }

    try:
        filepath = generate_resume_pdf(
            name=name,
            email=email,
            phone=phone,
            background=background,
            tailored_bullets=tailored_bullets,
            job_title=job_title,
            company=company,
            role_fit=role_fit,
            parsed_profile=parsed,
            linkedin_url=linkedin,
            github_url=github,
        )

        # Build download URL from filename
        filename = filepath.split("/")[-1] if "/" in filepath else filepath.split("\\")[-1]
        download_url = f"/download/{filename}"

        return {
            "resume_pdf_path": filepath,
            "resume_pdf_url": download_url,
            "messages": [
                {"role": "system", "content": f"resume_generator: PDF created at {filepath}"}
            ],
        }
    except Exception as e:
        return {
            "resume_pdf_path": "",
            "resume_pdf_url": "",
            "messages": [
                {"role": "system", "content": f"resume_generator: PDF generation failed: {e}"}
            ],
        }


def _extract_field(text: str, field: str, fallback: str = "") -> str:
    """Extract a named field from analysis text.

    Handles formats like:
        Job Title: Software Engineer
        **Job Title:** Software Engineer
        company: Acme Corp
    """
    import re
    patterns = [
        rf"\*?\*?{field}\*?\*?\s*[:\-]\s*(.+?)(?:\n|$)",
        rf"\*?\*?{fallback}\*?\*?\s*[:\-]\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().strip("*")
    return fallback or "Unknown"
