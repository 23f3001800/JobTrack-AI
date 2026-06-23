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
async def search_jobs(body: SearchRequest,
                      user: AuthUser = Depends(verify_user)):
    """Search for job postings matching a query.

    Returns structured results with titles, URLs, snippets, and
    detected source platform (LinkedIn, Indeed, etc.)
    """
    from tools.searcher import search_jobs_structured

    results = search_jobs_structured(
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
