# 6 tools — one per step of the job application workflow

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

TOOL_LOG_APPLICATION = {
    "name": "log_application",
    "description": "Save all generated outputs to workspace/ and log to tracker.json.",
    "input_schema": {
        "type": "object",
        "properties": {
            "company": {"type": "string"},
            "job_title": {"type": "string"},
            "cover_letter": {"type": "string"},
            "tailored_bullets": {"type": "string"},
            "outreach_dm": {"type": "string"}
        },
        "required": ["company", "job_title"]
    }
}

ALL_TOOLS = [
    TOOL_SCRAPE_JOB, TOOL_RESEARCH_COMPANY, TOOL_TAILOR_CV,
    TOOL_WRITE_COVER_LETTER, TOOL_WRITE_DM, TOOL_LOG_APPLICATION
]
