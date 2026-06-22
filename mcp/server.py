from mcp.server.fastmcp import FastMCP
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

WORKSPACE = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
WORKSPACE.mkdir(exist_ok=True)

mcp = FastMCP("jobtrack-filesystem")

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
    """Read a file from the workspace directory."""
    # WHY restrict to WORKSPACE? Security — without this check,
    # a malicious prompt could read "../../../etc/passwd"
    # Path.resolve() normalises the path, then we check it
    # starts with WORKSPACE to prevent directory traversal.
    path = (WORKSPACE / filename).resolve()
    if not str(path).startswith(str(WORKSPACE.resolve())):
        return "Error: Access denied — only workspace files allowed."
    if not path.exists():
        return f"File not found: {filename}"
    with open(path) as f:
        return f.read()

mcp.tool()
def write_file(filename: str, content: str) -> str:
    """Write or overwrite a file in the workspace directory."""
    path = (WORKSPACE / filename).resolve()
    if not str(path).startswith(str(WORKSPACE.resolve())):
        return "Error: Access denied."
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {len(content)} chars to {filename}"

@mcp.tool()
def get_tracker() -> str:
    """Return the job application tracker as formatted JSON."""
    tracker = WORKSPACE / "tracker.json"
    if not tracker.exists():
        return "No applications tracked yet."
    with open(tracker) as f:
        data = json.load(f)
    return json.dumps(data, indent=2)

# Run as stdio MCP server
if __name__ == "__main__":
    mcp.run(transport="stdio")
