import json, os
from datetime import datetime

WORKSPACE = os.getenv("WORKSPACE_DIR", "./workspace")

def execute_tool(name: str, args: dict) -> str:
    """Dispatch tool call to correct handler."""
    handlers = {
        "scrape_job_url":      _scrape_job_url,
        "research_company":    _research_company,
        "tailor_cv_bullets":   _tailor_cv_bullets,
        "write_cover_letter":  _write_cover_letter,
        "write_outreach_dm":   _write_outreach_dm,
        "log_application":     _log_application,
    }
    handler = handlers.get(name)
    if not handler:
        return f"Unknown tool: {name}"
    try:
        return handler(**args)
    except Exception as e:
        return f"Tool error ({name}): {str(e)}"
    
# ── Stubs (real code added Day 2) ─────────────────────
def _scrape_job_url(url: str) -> str:
    return f"[STUB] Job posting from {url}: Role=AI Engineer, Company=Acme, Requirements=Python LangGraph MCP"

def _research_company(company_name: str, job_title: str = "") -> str:
    return f"[STUB] {company_name}: AI-first startup, Series A, uses Python + FastAPI, values autonomy"

def _tailor_cv_bullets(job_requirements: str, company_profile: str) -> str:
    return "[STUB] Tailored bullets: • Built RAG systems • Deployed LangGraph agents • MCP integration"

def _write_cover_letter(job_analysis: str, company_profile: str, tailored_bullets: str) -> str:
    return "[STUB] Cover letter: Dear Hiring Manager, I am excited to apply for this role..."

def _write_outreach_dm(company_name: str, job_title: str, company_profile: str) -> str:
    return "[STUB] Hi [Name], I saw your work at {company_name}...".format(company_name=company_name)

def _log_application(company: str, job_title: str,
                     cover_letter: str = "", tailored_bullets: str = "",
                     outreach_dm: str = "") -> str:
    os.makedirs(WORKSPACE, exist_ok=True)
    slug = company.lower().replace(" ","_")
    entry = {"company": company, "job_title": job_title,
             "applied_at": datetime.now().isoformat(),
             "status": "applied"}
     # Save outputs
    if cover_letter:
        with open(f"{WORKSPACE}/{slug}_cover_letter.txt", "w") as f:
            f.write(cover_letter)
    # Append to tracker
    tracker = f"{WORKSPACE}/tracker.json"
    data = json.load(open(tracker)) if os.path.exists(tracker) else []
    data.append(entry)
    with open(tracker, "w") as f:
        json.dump(data, f, indent=2)
    return f"Logged application to {company} — files in {WORKSPACE}/"