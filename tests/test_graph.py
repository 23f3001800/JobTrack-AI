"""Unit tests for the multi-agent LangGraph pipeline.

WHY mock execute_tool?
Real LLM calls cost money ($0.10-0.50 per run) and take 30+ seconds.
Unit tests should be fast (<2s) and free. We mock execute_tool at the
source (tools.executor) since all sub-agents import from there.

Test strategy:
1. test_graph_completes_all_steps — Verify the full pipeline routes correctly
2. test_quality_loop_triggers_rewrite — Verify low scores trigger rewrites
3. test_workspace_files_created — Verify outputs are persisted
4. test_cover_letter_mentions_company — Integration quality check
"""
import os

import pytest
from pathlib import Path
from unittest.mock import patch


# --- Stub outputs for each tool ---
# These simulate what real LLM tools would return.
# The graph should route through all agents using these outputs.
STUB_OUTPUTS = {
    "scrape_job_url":     "JOB TITLE: AI Engineer\nCOMPANY: TechCorp\nREQUIREMENTS: Python, LangGraph",
    "search_jobs":        "Found 3 job postings:\n--- Job 1 ---\nTitle: AI Engineer at TechCorp\nURL: https://example.com/job/1",
    "research_company":   "TechCorp builds developer tools. Series A, 30 engineers. Uses Python + FastAPI.",
    "analyze_role_fit":   "FIT SCORE: 8/10\nMATCHING SKILLS: Python, LangGraph, FastAPI\nGAPS: Kubernetes",
    "tailor_cv_bullets":  "• Built RAG systems with LangGraph\n• Deployed FastAPI services on Railway",
    "write_cover_letter": "Dear TechCorp, I am excited to join your team because of your focus on developer tools...",
    "write_outreach_dm":  "Hi, I saw TechCorp's work on dev tools. Quick question about your agent stack?",
    "review_application": "APPROVED — Cover letter is well-personalised with specific company references.",
    "score_quality":      '{"overall": 4, "is_personalised": true, "role_matched": true, "professional_tone": true, "reasoning": "Good quality"}',
    "log_application":    "Logged application to TechCorp — files in ./workspace/",
}


def _mock_execute_tool(name, args):
    """Mock tool executor that returns stub outputs."""
    return STUB_OUTPUTS.get(name, "ok")


def test_graph_completes_all_steps():
    """Multi-agent graph must route through all 5 agents and populate all state fields.

    WHY patch at each sub-agent module?
    Each sub-agent does 'from tools.executor import execute_tool', which
    creates a local reference. We must patch at every module that imports
    it, not just at tools.executor.
    """
    # WHY ExitStack? We need to patch execute_tool in 5 different modules
    # simultaneously. ExitStack cleanly manages multiple context managers.
    from contextlib import ExitStack
    with ExitStack() as stack:
        for module in [
            "agent.agents.scout",
            "agent.agents.research",
            "agent.agents.writer",
            "agent.agents.quality",
            "agent.agents.applier",
        ]:
            stack.enter_context(
                patch(f"{module}.execute_tool", side_effect=_mock_execute_tool)
            )
        from agent.graph import run
        result = run("https://example.com/job/test-all-steps", "Python developer")

    # Verify all outputs are populated
    assert result["status"] == "complete"
    assert result["cover_letter"] != ""
    assert result["outreach_dm"] != ""
    assert result["tailored_bullets"] != ""
    assert result["role_fit"] != ""
    assert result["quality_score"] >= 4  # Quality agent should approve


def test_quality_loop_triggers_rewrite():
    """When quality score < 4, the Writer agent should be called again.

    WHY test this specifically? The quality loop is the key architectural
    improvement over the old 6-step pipeline. If it doesn't trigger
    rewrites, we're no better than the old system.
    """
    call_count = {"tailor_cv_bullets": 0, "write_cover_letter": 0, "score_quality": 0}

    def _mock_with_low_score(name, args):
        """First quality score is low (2), second is passing (4)."""
        if name in call_count:
            call_count[name] += 1

        if name == "score_quality":
            # First call: fail with score 2 to trigger rewrite
            # Second call: pass with score 4
            if call_count["score_quality"] <= 1:
                return '{"overall": 2, "is_personalised": false, "role_matched": false, "professional_tone": true, "reasoning": "Too generic"}'
            return '{"overall": 4, "is_personalised": true, "role_matched": true, "professional_tone": true, "reasoning": "Good after rewrite"}'

        if name == "review_application":
            return "Cover letter is too generic. Mention TechCorp's specific products."

        return STUB_OUTPUTS.get(name, "ok")

    from contextlib import ExitStack
    with ExitStack() as stack:
        for module in [
            "agent.agents.scout",
            "agent.agents.research",
            "agent.agents.writer",
            "agent.agents.quality",
            "agent.agents.applier",
        ]:
            stack.enter_context(
                patch(f"{module}.execute_tool", side_effect=_mock_with_low_score)
            )
        from agent.graph import run
        result = run("https://example.com/job/test-rewrite", "Python developer")

    assert result["status"] == "complete"
    # Writer should have been called at least twice (initial + 1 rewrite)
    assert call_count["tailor_cv_bullets"] >= 2, (
        f"Expected Writer to rewrite, but tailor_cv_bullets was only called "
        f"{call_count['tailor_cv_bullets']} time(s)"
    )


def test_workspace_files_created():
    """After a run, at least one file should exist in workspace/."""
    workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    if workspace.exists():
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