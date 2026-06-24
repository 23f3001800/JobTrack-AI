"""Job search and management routes.

WHY separate from the /run endpoint?
/run executes the full multi-agent pipeline on a KNOWN job URL.
These routes let users DISCOVER jobs first, save them to their
pipeline, and then run the agent on selected ones.

Flow: Search → Save → Run agent → Track application
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.auth import AuthUser, verify_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


class SearchRequest(BaseModel):
    query: str = Field(..., description="Job title, skills, or keywords")
    location: str = Field("", description="Optional location filter")
    max_results: int = Field(10, ge=1, le=20)


class SaveJobRequest(BaseModel):
    url: str
    title: str = ""
    company: str = ""
    source: str = "manual"


@router.post("/search")
async def search_jobs_endpoint(body: SearchRequest,
                      user: AuthUser = Depends(verify_user)):
    """Search for job postings matching a query.

    Returns structured results with titles, URLs, snippets, and
    detected source platform (LinkedIn, Indeed, etc.)
    """
    from tools.job_search import search_jobs

    results = search_jobs(
        query=body.query,
        location=body.location,
        max_results=body.max_results,
    )

    return {
        "query": body.query,
        "location": body.location,
        "results": results,
        "total": len(results),
    }


@router.post("/save")
async def save_job(body: SaveJobRequest,
                   user: AuthUser = Depends(verify_user)):
    """Save a discovered job to the user's pipeline.

    WHY save before running the agent?
    Users want to batch-discover jobs, review them, then selectively
    run the agent on the best matches. Saving creates a "pipeline"
    of potential jobs to apply to.
    """
    from db import get_db
    db = get_db()

    job = db.save_job(
        data={
            "url": body.url,
            "title": body.title,
            "company": body.company,
            "source": body.source,
        },
        user_id=user.user_id,
    )

    return {"message": "Job saved", "job": job}


@router.get("/providers")
async def get_providers(user: AuthUser = Depends(verify_user)):
    """Return available job search providers and their status."""
    from tools.job_search import get_available_providers
    return {"providers": get_available_providers()}


class DiscoverRequest(BaseModel):
    provider: str = Field("auto", description="Search provider: serpapi, himalayas, or auto")
    location: str = Field("", description="Optional location filter")
    role: str = Field("", description="Target role override (auto-inferred from resume if empty)")
    max_results: int = Field(20, ge=1, le=25)


@router.post("/discover")
async def discover_jobs(body: DiscoverRequest,
                        user: AuthUser = Depends(verify_user)):
    """Resume-driven job discovery — no manual query needed.

    Analyzes the user's uploaded resume to generate search queries,
    then searches across providers and ranks results by relevance.
    If a role override is provided, it's used instead of auto-inference.
    """
    from db import get_db
    from tools.job_matcher import generate_search_queries, rank_jobs
    from tools.job_search import search_jobs

    db = get_db()
    profile = db.get_profile(user.user_id)
    parsed_profile = profile.get("parsed_profile", {})

    if not parsed_profile:
        return {"error": "No resume uploaded. Complete onboarding first.", "results": []}

    # Infer role from profile for display
    inferred_role = _infer_role(parsed_profile)

    # Generate search queries from resume (optionally with role override)
    if body.role.strip():
        # User provided a role override — generate focused queries
        queries = [{"query": f"{body.role.strip()} {body.location}".strip()}]
        # Also add skill-augmented variations
        skills = parsed_profile.get("skills", [])
        if skills:
            top_skills = " ".join(skills[:3])
            queries.append({"query": f"{body.role.strip()} {top_skills}"})
    else:
        queries = generate_search_queries(parsed_profile)

    # Search across all generated queries
    all_jobs = []
    seen_urls = set()
    for q in queries:
        results = search_jobs(
            query=q["query"],
            provider=body.provider,
            location=body.location or q.get("location", ""),
            max_results=body.max_results,
        )
        for job in results:
            url = job.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_jobs.append(job)

    # Rank by relevance to profile
    ranked = rank_jobs(all_jobs, parsed_profile)

    return {
        "queries_used": queries,
        "provider": body.provider,
        "inferred_role": body.role.strip() or inferred_role,
        "results": ranked[:body.max_results],
        "total": len(ranked),
    }


def _infer_role(parsed_profile: dict) -> str:
    """Infer a proper job title from parsed resume profile.

    Priority: experience titles > keyword matching on skills/education/summary > fallback.
    WHY not use the summary directly? Summaries like "BS Data Science fresher
    from IIT Madras with hands-on experience..." are descriptions, not job titles.
    """
    # 1. Try from experience titles
    experience = parsed_profile.get("experience", [])
    for exp in experience:
        if isinstance(exp, dict):
            title = exp.get("title", "")
            if title and len(title) < 60:
                return title

    # 2. Keyword-based role mapping from skills + education + summary
    ROLE_KEYWORDS = [
        (["data science", "machine learning", "ml", "deep learning", "pytorch", "tensorflow", "nlp"], "Data Scientist"),
        (["data engineer", "etl", "airflow", "spark", "data pipeline"], "Data Engineer"),
        (["data analyst", "tableau", "power bi", "analytics"], "Data Analyst"),
        (["frontend", "react", "vue", "angular", "next.js"], "Frontend Developer"),
        (["backend", "node.js", "express", "django", "flask", "fastapi"], "Backend Developer"),
        (["full stack", "fullstack", "mern", "mean"], "Full Stack Developer"),
        (["devops", "kubernetes", "docker", "ci/cd", "terraform"], "DevOps Engineer"),
        (["android", "ios", "react native", "flutter", "mobile"], "Mobile Developer"),
        (["python", "java", "golang", "rust", "c++"], "Software Engineer"),
        (["product manager", "product management"], "Product Manager"),
        (["ui/ux", "ux design", "figma"], "UI/UX Designer"),
    ]

    skills = parsed_profile.get("skills", [])
    education = parsed_profile.get("education", [])
    summary = parsed_profile.get("summary", "")

    blob = " ".join([
        " ".join(s.lower() for s in skills),
        " ".join(
            (e.get("degree", "") if isinstance(e, dict) else str(e)).lower()
            for e in education
        ),
        summary.lower(),
    ])

    for keywords, role in ROLE_KEYWORDS:
        if any(kw in blob for kw in keywords):
            return role

    # 3. Degree-based fallback
    for edu in education:
        if isinstance(edu, dict):
            degree = edu.get("degree", "").lower()
            if "data science" in degree:
                return "Data Scientist"
            if "computer" in degree:
                return "Software Engineer"

    # 4. Skills-based fallback
    if skills:
        return f"{skills[0]} Developer"

    return "Software Engineer"


