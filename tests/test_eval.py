"""Tests for the eval framework — verifies evaluator output format.

WHY mock the LLM call?
Real evaluations cost money and are slow. These tests verify
that the evaluator correctly parses LLM output and computes
aggregate metrics. The actual LLM scoring quality is tested
by running `python -m eval.run_eval` on real applications.
"""
import json
from unittest.mock import patch, MagicMock

from eval.evaluator import evaluate_application, evaluate_batch


# Simulated Claude response for eval
MOCK_EVAL_RESPONSE = json.dumps({
    "overall": 4,
    "is_personalised": True,
    "role_matched": True,
    "professional_tone": True,
    "reasoning": "Strong application with specific company references and matching skills.",
})


def _mock_anthropic_response(text: str):
    """Create a mock Anthropic response object."""
    mock = MagicMock()
    mock.content = [MagicMock(text=text)]
    return mock


@patch("eval.evaluator.anthropic.Anthropic")
def test_evaluate_single_application(mock_client_class):
    """Test that single application evaluation returns correct format."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_anthropic_response(
        MOCK_EVAL_RESPONSE
    )
    mock_client_class.return_value = mock_client

    result = evaluate_application(
        job_analysis="AI Engineer at TechCorp. Requires Python, LangGraph.",
        cover_letter="Dear TechCorp, I built RAG systems with LangGraph...",
        tailored_bullets="• Built LangGraph pipelines\n• Deployed FastAPI services",
        company="TechCorp",
    )

    # Verify structure
    assert result["overall"] == 4
    assert result["is_personalised"] is True
    assert result["role_matched"] is True
    assert result["professional_tone"] is True
    assert "company" in result
    assert result["company"] == "TechCorp"


@patch("eval.evaluator.anthropic.Anthropic")
def test_evaluate_batch_metrics(mock_client_class):
    """Test that batch evaluation computes correct aggregate metrics."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_anthropic_response(
        MOCK_EVAL_RESPONSE
    )
    mock_client_class.return_value = mock_client

    apps = [
        {
            "job_analysis": "Engineer at A",
            "cover_letter": "Dear A...",
            "tailored_bullets": "• Built X",
            "company": "CompanyA",
        },
        {
            "job_analysis": "Engineer at B",
            "cover_letter": "Dear B...",
            "tailored_bullets": "• Built Y",
            "company": "CompanyB",
        },
    ]

    results = evaluate_batch(apps)

    assert results["avg_score"] == 4.0
    assert results["pass_rate"] == "2/2"
    assert len(results["results"]) == 2


@patch("eval.evaluator.anthropic.Anthropic")
def test_evaluate_handles_malformed_json(mock_client_class):
    """Test graceful handling when Claude returns non-JSON."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_anthropic_response(
        "This is not valid JSON at all"
    )
    mock_client_class.return_value = mock_client

    result = evaluate_application(
        job_analysis="test",
        cover_letter="test",
        tailored_bullets="test",
        company="TestCo",
    )

    # Should return fallback result, not crash
    assert result["overall"] == 0
    assert "Failed to parse" in result["reasoning"]


@patch("eval.evaluator.anthropic.Anthropic")
def test_evaluate_handles_markdown_wrapped_json(mock_client_class):
    """Test parsing JSON wrapped in markdown code blocks."""
    mock_client = MagicMock()
    # Claude sometimes wraps JSON in ```json blocks
    wrapped = f"```json\n{MOCK_EVAL_RESPONSE}\n```"
    mock_client.messages.create.return_value = _mock_anthropic_response(wrapped)
    mock_client_class.return_value = mock_client

    result = evaluate_application(
        job_analysis="test",
        cover_letter="test",
        tailored_bullets="test",
        company="TestCo",
    )

    assert result["overall"] == 4
