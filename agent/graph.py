"""Multi-agent LangGraph for JobTrack AI.

Architecture:
    Supervisor (deterministic router)
        ├── Scout Agent        → scrape job URL
        ├── Research Agent     → company research + role fit
        ├── Writer Agent       → cover letter, CV bullets, DM
        ├── Resume Generator   → tailored PDF resume
        ├── Quality Agent      → review + score (rewrite loop)
        └── Apply Agent        → log application (or pause for review)

The supervisor checks state after each agent completes and routes
to the next agent. The Writer ↔ Quality loop runs up to 2 times
to improve output quality before proceeding to Apply.

WHY LangGraph instead of a simple for-loop?
1. Checkpointing: Resume from any step on failure
2. Streaming: Frontend gets step-by-step progress updates
3. Conditional edges: Quality loop requires dynamic routing
4. Tracing: LangSmith traces each agent as a separate span
5. Future: Parallel execution (Scout + Research) via fan-out
"""
import operator
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

# Import sub-agent runners
from agent.agents.applier import run_applier
from agent.agents.quality import run_quality
from agent.agents.research import run_research
from agent.agents.resume_generator import run_resume_generator
from agent.agents.scout import run_scout
from agent.agents.supervisor import route_next_agent
from agent.agents.writer import run_writer

load_dotenv()

if os.getenv("LANGCHAIN_TRACING_V2") == "true":
    os.environ.setdefault("LANGCHAIN_PROJECT", "jobtrack-ai")


class JobState(TypedDict):
    """Shared state across all agents in the multi-agent system.

    WHY TypedDict instead of a Pydantic model?
    LangGraph requires TypedDict for state — it uses the type hints
    to validate state transitions and generate the state schema.

    Fields are grouped by which agent populates them.
    """

    # --- Input (provided by user) ---
    job_url: str  # The job posting URL to process
    user_background: str  # User's background/experience summary
    cv_text: str  # User's CV text (extracted from uploaded PDF)
    user_id: str  # User ID for scoping applications
    user_profile: dict  # Full user profile with parsed_profile for PDF generation

    # --- Scout Agent outputs ---
    job_analysis: str  # Structured job details (title, requirements, etc.)

    # --- Research Agent outputs ---
    company_profile: str  # Company info (product, culture, tech stack)
    role_fit: str  # Fit analysis (score, matching skills, gaps)

    # --- Writer Agent outputs ---
    tailored_bullets: str  # CV bullets rewritten for this specific role
    cover_letter: str  # Personalised 3-paragraph cover letter
    outreach_dm: str  # LinkedIn cold DM

    # --- Resume Generator outputs ---
    resume_pdf_path: str  # Local file path to generated PDF
    resume_pdf_url: str  # Download URL for the PDF (/download/filename.pdf)

    # --- Quality Agent outputs ---
    quality_score: int  # 1-5 quality rating
    quality_feedback: str  # Detailed feedback for rewrite (empty if approved)
    quality_attempts: int  # Number of quality review cycles completed

    # --- Apply Agent outputs ---
    log_result: str  # Confirmation that application was logged

    # --- Orchestration ---
    messages: Annotated[list, operator.add]  # Message history for tracing/streaming
    iterations: int  # Safety counter to prevent infinite loops


# ──────────────────────────────────────────────
# Build the multi-agent graph
# ──────────────────────────────────────────────

builder = StateGraph(JobState)

# Register each sub-agent as a node.
# WHY separate nodes per agent? Each node appears as a distinct step
# in LangSmith traces and in the streaming API response, giving the
# frontend real-time progress updates ("Researching company...")
builder.add_node("scout", run_scout)
builder.add_node("research", run_research)
builder.add_node("writer", run_writer)
builder.add_node("resume_generator", run_resume_generator)
builder.add_node("quality", run_quality)
builder.add_node("applier", run_applier)

# Entry point: always start with scout (scrape the job first).
builder.set_entry_point("scout")

# After each agent, the supervisor routes to the next one.
# WHY not set_entry_point("supervisor")?
# The supervisor is a pure function, not a node. It runs as
# a conditional edge function — more efficient than a separate node
# that would consume a LangGraph step without doing useful work.
_routing_map = {
    "scout": "scout",
    "research": "research",
    "writer": "writer",
    "resume_generator": "resume_generator",
    "quality": "quality",
    "applier": "applier",
    "end": END,
}

for agent_name in ["scout", "research", "writer", "resume_generator", "quality", "applier"]:
    builder.add_conditional_edges(agent_name, route_next_agent, _routing_map)

# Checkpointing: MemorySaver for development.
# WHY not PostgresSaver? We'll add Supabase-backed checkpointing
# in Phase 2 when the database is set up. MemorySaver works for
# single-process development but loses state on restart.
checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)


def run(job_url: str, user_background: str, cv_text: str = "",
        user_id: str = "") -> dict:
    """Run the full multi-agent pipeline on a job URL.

    Args:
        job_url: The job posting URL to process.
        user_background: The user's experience/skills summary.
        cv_text: The user's CV text (from uploaded resume).

    Returns:
        Dict with status, cover_letter, outreach_dm, tailored_bullets,
        quality_score, and role_fit analysis.
    """
    # WHY use URL slug as thread_id? Ensures that re-running the same
    # URL resumes from the last checkpoint instead of starting over.
    # This saves money on retries after transient failures.
    thread_id = job_url.split("/")[-1]

    initial = JobState(
        job_url=job_url,
        user_background=user_background,
        cv_text=cv_text,
        user_id=user_id,
        user_profile={},
        job_analysis="",
        company_profile="",
        role_fit="",
        tailored_bullets="",
        cover_letter="",
        outreach_dm="",
        resume_pdf_path="",
        resume_pdf_url="",
        quality_score=0,
        quality_feedback="",
        quality_attempts=0,
        log_result="",
        messages=[],
        iterations=0,
    )

    config = {"configurable": {"thread_id": thread_id}}
    final = app.invoke(initial, config=config)

    return {
        "status": "complete",
        "cover_letter": final.get("cover_letter"),
        "outreach_dm": final.get("outreach_dm"),
        "tailored_bullets": final.get("tailored_bullets"),
        "quality_score": final.get("quality_score"),
        "role_fit": final.get("role_fit"),
        "resume_pdf_url": final.get("resume_pdf_url"),
    }