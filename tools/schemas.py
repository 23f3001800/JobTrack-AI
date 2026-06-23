# 9 tools grouped by the agent that owns them.
# Each agent only receives the subset it needs, but all schemas live here
# as a single source of truth to avoid drift between agent configs.

# ---------------------------------------------------------------------------
# Scout Agent Tools — responsible for scraping and parsing job postings
# ---------------------------------------------------------------------------

TOOL_SCRAPE_JOB = {
    "name": "scrape_job_url",
    "description": "Scrape a job posting URL and extract: title, company, requirements, responsibilities, salary, location.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Full URL of the job posting"}
        },
        "required": ["url"]
    }
}

# ---------------------------------------------------------------------------
# Research Agent Tools — company research and candidate fit analysis
# ---------------------------------------------------------------------------

TOOL_RESEARCH_COMPANY = {
    "name": "research_company",
    "description": "Search the web for company info: product, culture, tech stack, recent news, funding.",
    "input_schema": {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "job_title": {"type": "string"}
        },
        "required": ["company_name"]
    }
}

# WHY analyze_role_fit lives with Research, not Writer:
# Fit analysis is an analytical/research task — it assesses the candidate
# BEFORE any writing begins. The Writer agent consumes its output but
# shouldn't own the analysis step.
TOOL_ANALYZE_ROLE_FIT = {
    "name": "analyze_role_fit",
    "description": "Compare job requirements against the candidate's background. Returns fit score, matching skills, gaps, and talking points. Run BEFORE writing materials to inform the Writer agent.",
    "input_schema": {
        "type": "object",
        "properties": {
            "job_analysis": {"type": "string", "description": "The scraped job analysis from step 1"},
            "user_background": {"type": "string", "description": "The user's background and CV summary"}
        },
        "required": ["job_analysis", "user_background"]
    }
}

# ---------------------------------------------------------------------------
# Writer Agent Tools — CV tailoring, cover letters, and outreach DMs
# ---------------------------------------------------------------------------

TOOL_TAILOR_CV = {
    "name": "tailor_cv_bullets",
    "description": "Read master CV and rewrite bullet points to match job requirements. Returns tailored bullets.",
    "input_schema": {
        "type": "object",
        "properties": {
            "job_requirements": {"type": "string"},
            "company_profile": {"type": "string"}
        },
        "required": ["job_requirements", "company_profile"]
    }
}
TOOL_WRITE_COVER_LETTER = {
    "name": "write_cover_letter",
    "description": "Write a personalised 3-paragraph cover letter using job analysis + company profile + tailored CV bullets.",
    "input_schema": {
        "type": "object",
        "properties": {
            "job_analysis": {"type": "string"},
            "company_profile": {"type": "string"},
            "tailored_bullets": {"type": "string"}
        },
        "required": ["job_analysis", "company_profile", "tailored_bullets"]
    }
}
TOOL_WRITE_DM = {
    "name": "write_outreach_dm",
    "description": "Draft a personalised LinkedIn cold DM to an employee at the company. Short, specific, not salesy.",
    "input_schema": {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "job_title": {"type": "string"},
            "company_profile": {"type": "string"}
        },
        "required": ["company_name", "job_title", "company_profile"]
    }
}

# ---------------------------------------------------------------------------
# Quality Agent Tools — self-review system that catches generic AI content
# WHY these are separate tools (not one combined tool):
# review_application returns prose feedback for the Writer's rewrite loop.
# score_quality returns structured JSON for programmatic pass/fail gates.
# Combining them into one prompt degrades both outputs.
# ---------------------------------------------------------------------------

TOOL_REVIEW_APPLICATION = {
    "name": "review_application",
    "description": "Review all generated application materials and provide specific, actionable feedback for improvement. Returns detailed critique with rewrite suggestions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "job_analysis": {"type": "string"},
            "company_profile": {"type": "string"},
            "cover_letter": {"type": "string"},
            "tailored_bullets": {"type": "string"}
        },
        "required": ["job_analysis", "company_profile", "cover_letter", "tailored_bullets"]
    }
}

TOOL_SCORE_QUALITY = {
    "name": "score_quality",
    "description": "Score application quality on 1-5 scale. Returns JSON with overall score, personalisation flag, role match flag, and reasoning.",
    "input_schema": {
        "type": "object",
        "properties": {
            "job_analysis": {"type": "string"},
            "company_profile": {"type": "string"},
            "cover_letter": {"type": "string"},
            "tailored_bullets": {"type": "string"}
        },
        "required": ["job_analysis", "company_profile", "cover_letter", "tailored_bullets"]
    }
}

# ---------------------------------------------------------------------------
# Apply Agent Tools — persists outputs and logs the application
# ---------------------------------------------------------------------------

TOOL_LOG_APPLICATION = {
    "name": "log_application",
    "description": "Save all generated outputs to workspace/ and log to tracker.json. Pass ALL generated content so it is persisted.",
    "input_schema": {
        "type": "object",
        "properties": {
            "company": {"type": "string"},
            "job_title": {"type": "string"},
            "cover_letter": {"type": "string", "description": "The full cover letter text"},
            "tailored_bullets": {"type": "string", "description": "The tailored CV bullet points"},
            "outreach_dm": {"type": "string", "description": "The LinkedIn outreach DM"},
            "job_analysis": {"type": "string", "description": "The scraped job analysis from step 1"},
            "company_profile": {"type": "string", "description": "The company research profile from step 2"}
        },
        "required": ["company", "job_title"]
    }
}

# Master list in pipeline execution order: scout → research → write → review → apply
ALL_TOOLS = [
    TOOL_SCRAPE_JOB, TOOL_RESEARCH_COMPANY, TOOL_ANALYZE_ROLE_FIT,
    TOOL_TAILOR_CV, TOOL_WRITE_COVER_LETTER, TOOL_WRITE_DM,
    TOOL_REVIEW_APPLICATION, TOOL_SCORE_QUALITY, TOOL_LOG_APPLICATION
]
