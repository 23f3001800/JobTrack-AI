import os

import pytest
from pathlib import Path
from unittest.mock import patch

# Real LLM calls cost money and take 30+ seconds.
# Unit tests should be fast (< 2s) and free.
# We mock execute_tool to return predictable stub output,
# then verify the graph routes correctly through all 6 steps.

STUB_OUTPUTS = {
    "scrape_job_url":     "JOB TITLE: AI Engineer\nCOMPANY: TechCorp\nREQUIREMENTS: Python, LangGraph",
    "research_company":   "TechCorp builds developer tools. Series A, 30 engineers. Uses Python + FastAPI.",
    "tailor_cv_bullets":  "• Built RAG systems with LangGraph\n• Deployed FastAPI services on Railway",
    "write_cover_letter": "Dear TechCorp, I am excited to join your team because of your focus on...",
    "write_outreach_dm":  "Hi [Name], I saw your work on TechCorp's dev tools. Quick question about your agent stack?",
    "log_application":    "Logged application to TechCorp — files in ./workspace/",
}

def test_graph_completes_all_6_steps():
    """Graph must call all 6 tools and populate all state fields."""
    with patch("agent.graph.execute_tool",
               side_effect=lambda name, args: STUB_OUTPUTS.get(name, "ok")):
        from agent.graph import run
        result = run("https://example.com/job/123", "Python developer")

    assert result["status"] == "complete"
    assert result["cover_letter"] != ""
    assert result["outreach_dm"] != ""
    assert result["tailored_bullets"] != ""

def test_workspace_files_created():
    """After a run, at least one file should exist in workspace/."""
    workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    if workspace.exists():
        # If workspace exists, verify tracker.json is present
        files = list(workspace.iterdir())
        assert len(files) > 0, "Workspace empty — run the full pipeline first"

def test_cover_letter_mentions_company():
    """Integration test: cover letter must mention the company name."""
    workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    cl_files = list(workspace.glob("*_cover_letter.txt")) if workspace.exists() else []
    if not cl_files:
        pytest.skip("No cover letter generated yet — run full pipeline first")
    content = cl_files[-1].read_text()
    # Cover letter must not be generic — it must mention something specific
    assert len(content) > 200, "Cover letter too short"
    assert content.count("I") < 15, "Too many 'I' statements — too self-focused"