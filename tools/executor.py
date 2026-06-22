import json
import os
from datetime import datetime
from langsmith import traceable
from tools.scraper import scrape_job_url as _scrape_real
from tools.researcher import research_company as _research_real
from tools.cv_processor import tailor_cv_bullets as _tailor_real
from tools.cv_processor import write_cover_letter as _letter_real


WORKSPACE = os.getenv("WORKSPACE_DIR", "./workspace")

@traceable(name="tool-executor")
def execute_tool(name: str, args: dict) -> str:
    from langsmith import get_current_run_tree
    run = get_current_run_tree()
    if run:
        run.add_metadata({"tool_name": name, "tool_args": list(args.keys())})

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
        result = handler(**args)
        if run:
            run.add_metadata({"result_length": len(result)})
        return result
    except Exception as e:
        if run:
            run.add_metadata({"error": str(e)})
        return f"Tool error ({name}): {e}"
    

def _scrape_job_url(url: str) -> str:
    return _scrape_real(url)

def _research_company(company_name: str, job_title: str = "") -> str:
    return _research_real(company_name, job_title)

def _tailor_cv_bullets(job_requirements: str, company_profile: str) -> str:
    return _tailor_real(job_requirements, company_profile)

def _write_cover_letter(job_analysis: str, company_profile: str,
                        tailored_bullets: str) -> str:
    return _letter_real(job_analysis, company_profile, tailored_bullets)

def _write_outreach_dm(company_name: str, job_title: str,
                      company_profile: str) -> str:
    # WHY write the DM with Claude directly here (not a separate file)?
    # DM writing is simple enough to not need its own module.
    # It's one LLM call with clear inputs — keeping it in executor
    # avoids over-engineering a 10-line function.
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role":"user","content":
            f"""Write a LinkedIn cold DM to an employee at {company_name}.
I'm applying for {job_title}. Reference something specific from the company profile.
Ask ONE specific technical question about their stack or approach.
Under 100 words. Not salesy. Sound like a curious engineer, not a job beggar.

Company profile: {company_profile[:300]}"""}]
    )
    return resp.content[0].text



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

