import os
from langsmith import traceable
from tools.scraper import scrape_job_url as _scrape_real
from tools.searcher import search_jobs as _search_real
from tools.researcher import research_company as _research_real
from tools.researcher import analyze_role_fit as _role_fit_real
from tools.cv_processor import tailor_cv_bullets as _tailor_real
from tools.cv_processor import write_cover_letter as _letter_real
from tools.quality import review_application as _review_real
from tools.quality import score_quality as _score_real


WORKSPACE = os.getenv("WORKSPACE_DIR", "./workspace")

@traceable(name="tool-executor")
def execute_tool(name: str, args: dict) -> str:
    from langsmith import get_current_run_tree
    run = get_current_run_tree()
    if run:
        run.add_metadata({"tool_name": name, "tool_args": list(args.keys())})

    """Dispatch tool call to correct handler."""
    # Dispatch table — maps tool names from schemas.py to handler functions.
    # Order mirrors the pipeline: scout → research → write → review → apply.
    handlers = {
        "scrape_job_url":      _scrape_job_url,
        "search_jobs":         _search_jobs,
        "research_company":    _research_company,
        "analyze_role_fit":    _analyze_role_fit,
        "tailor_cv_bullets":   _tailor_cv_bullets,
        "write_cover_letter":  _write_cover_letter,
        "write_outreach_dm":   _write_outreach_dm,
        "review_application":  _review_application,
        "score_quality":       _score_quality,
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

def _search_jobs(query: str, location: str = "", max_results: int = 10) -> str:
    """Search for job postings matching a query."""
    return _search_real(query, location, max_results)

def _research_company(company_name: str, job_title: str = "") -> str:
    return _research_real(company_name, job_title)


def _analyze_role_fit(job_analysis: str, user_background: str) -> str:
    """Assess candidate-job fit before the Writer agent starts."""
    return _role_fit_real(job_analysis, user_background)

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


# --- Quality Agent wrappers ---
# WHY thin wrappers instead of calling quality.py directly from handlers dict?
# Consistency with the existing pattern lets LangSmith tracing and error
# handling in execute_tool treat every tool identically. Also leaves room
# for adding executor-level caching or retries per-tool later.

def _review_application(job_analysis: str, company_profile: str,
                        cover_letter: str, tailored_bullets: str) -> str:
    """Get prose feedback on application materials for the rewrite loop."""
    return _review_real(job_analysis, company_profile, cover_letter, tailored_bullets)


def _score_quality(job_analysis: str, company_profile: str,
                   cover_letter: str, tailored_bullets: str) -> str:
    """Get structured JSON quality score for programmatic gates."""
    return _score_real(job_analysis, company_profile, cover_letter, tailored_bullets)



def _log_application(company: str, job_title: str,
                     cover_letter: str = "", tailored_bullets: str = "",
                     outreach_dm: str = "", job_analysis: str = "",
                     company_profile: str = "") -> str:
    """Log a completed application to the database.

    WHY delegate to db.get_db() instead of writing JSON directly?
    The db layer handles both Supabase (production) and JSON fallback
    (local dev) transparently. This function doesn't need to know
    which backend is active.
    """
    from db import get_db
    db = get_db()

    db.log_application({
        "company": company,
        "job_title": job_title,
        "cover_letter": cover_letter,
        "tailored_bullets": tailored_bullets,
        "outreach_dm": outreach_dm,
        "job_analysis": job_analysis,
        "company_profile": company_profile,
    })

    return f"Logged application to {company}"

