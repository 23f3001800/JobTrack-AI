"""MCP Server — Claude Desktop integration for AutoApply AI.

This exposes AutoApply's capabilities as MCP tools that Claude Desktop
can call directly. Users can ask Claude:
- "Search for Python AI engineer jobs in London"
- "List my applications"
- "Read my cover letter for TechCorp"
- "Run the agent on this job URL"
- "What's my application quality score?"

HOW IT WORKS:
Claude Desktop spawns this as a subprocess via stdio transport.
Each @mcp.tool() becomes a tool that Claude can call. The tools
talk to the same backend (workspace files, DB, agents) as the API.

SETUP in claude_desktop_config.json:
{
  "mcpServers": {
    "autoapply": {
      "command": "python",
      "args": ["/path/to/mcp/server.py"]
    }
  }
}
"""
from mcp.server.fastmcp import FastMCP
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

WORKSPACE = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
WORKSPACE.mkdir(exist_ok=True)

mcp = FastMCP("autoapply-ai")


# ── Workspace Tools ──

@mcp.tool()
def list_workspace() -> str:
    """List all files in the job application workspace."""
    files = list(WORKSPACE.iterdir())
    if not files:
        return "Workspace is empty — no applications saved yet."
    lines = []
    for f in sorted(files):
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"{f.name} ({size} bytes, modified {mtime})")
    return "\n".join(lines)


@mcp.tool()
def read_file(filename: str) -> str:
    """Read a file from the workspace directory.

    WHY restrict to WORKSPACE? Security — without this check,
    a malicious prompt could read '../../../etc/passwd'.
    Path.resolve() normalises the path, then we check it
    starts with WORKSPACE to prevent directory traversal.
    """
    path = (WORKSPACE / filename).resolve()
    if not str(path).startswith(str(WORKSPACE.resolve())):
        return "Error: Access denied — only workspace files allowed."
    if not path.exists():
        return f"File not found: {filename}"
    with open(path) as f:
        return f.read()


@mcp.tool()
def write_file(filename: str, content: str) -> str:
    """Write or overwrite a file in the workspace directory."""
    path = (WORKSPACE / filename).resolve()
    if not str(path).startswith(str(WORKSPACE.resolve())):
        return "Error: Access denied."
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {len(content)} chars to {filename}"


# ── Tracker Tools ──

@mcp.tool()
def get_tracker() -> str:
    """Return all tracked job applications as formatted JSON.

    Shows: company, job title, status, quality score, date applied.
    """
    tracker = WORKSPACE / "tracker.json"
    if not tracker.exists():
        return "No applications tracked yet."
    with open(tracker) as f:
        data = json.load(f)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_application(company: str) -> str:
    """Get details for a specific company's application.

    Returns cover letter, tailored bullets, and outreach DM if available.
    """
    results = []
    for suffix in ["cover_letter", "cv_bullets", "outreach_dm", "job_analysis"]:
        # Try various filename patterns
        for pattern in [
            f"{company}_{suffix}.md",
            f"{company.replace(' ', '_')}_{suffix}.md",
            f"{company.lower().replace(' ', '_')}_{suffix}.md",
        ]:
            path = WORKSPACE / pattern
            if path.exists():
                with open(path) as f:
                    results.append(f"## {suffix.replace('_', ' ').title()}\n{f.read()}")
                break

    if not results:
        return f"No application files found for '{company}'."
    return "\n\n".join(results)


# ── Search Tools ──

@mcp.tool()
def search_jobs(query: str, location: str = "") -> str:
    """Search the web for job postings matching a query.

    Args:
        query: Job title, skills, or keywords (e.g. 'Python AI engineer')
        location: Optional location filter (e.g. 'London', 'remote')

    Returns: List of job postings with titles, URLs, and previews.
    """
    from tools.searcher import search_jobs as _search
    return _search(query, location, max_results=10)


# ── Agent Tools ──

@mcp.tool()
def run_agent(job_url: str) -> str:
    """Run the full multi-agent pipeline on a job URL.

    Executes: Scout → Research → Writer → Quality → Applier
    Returns a summary of all generated materials.

    WHY expose the full pipeline via MCP?
    Power users can say "Apply to this job: <URL>" in Claude Desktop
    and get the full application package without opening the dashboard.
    """
    try:
        from agent.graph import app as agent_app, JobState

        initial = JobState(
            job_url=job_url,
            messages=[],
            current_agent="",
            job_analysis="",
            company_profile="",
            role_fit="",
            tailored_bullets="",
            cover_letter="",
            outreach_dm="",
            quality_score=0,
            quality_feedback="",
            rewrite_count=0,
        )

        final = agent_app.invoke(initial)

        return (
            f"✅ Application complete for {job_url}\n\n"
            f"## Cover Letter\n{final.get('cover_letter', 'N/A')}\n\n"
            f"## Tailored CV Bullets\n{final.get('tailored_bullets', 'N/A')}\n\n"
            f"## Outreach DM\n{final.get('outreach_dm', 'N/A')}\n\n"
            f"## Quality Score: {final.get('quality_score', 0)}/5"
        )
    except Exception as e:
        return f"Agent error: {e}"


# ── Run as stdio MCP server ──
if __name__ == "__main__":
    mcp.run(transport="stdio")
