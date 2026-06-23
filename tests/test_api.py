"""API Integration Tests — tests the FastAPI endpoints end-to-end.

WHY integration tests in addition to unit tests?
Unit tests (test_graph.py) verify the agent pipeline in isolation.
Integration tests verify that the API layer correctly:
- Authenticates requests
- Validates input
- Returns correct status codes and response shapes
- Handles errors gracefully

These tests use FastAPI's TestClient which runs the full middleware
stack (auth, logging, error handling) without starting a real server.
"""
import os
from unittest.mock import patch
from fastapi.testclient import TestClient

# Set API_KEY before importing the app (auth module reads it at import time)
os.environ.setdefault("API_KEY", "test-api-key-12345")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

from api.main import app  # noqa: E402

client = TestClient(app)

# Auth header for API key authentication
AUTH_HEADERS = {"Authorization": "Bearer test-api-key-12345"}


# ── Health Check ──

def test_health_no_auth():
    """Health endpoint requires no authentication."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "agents" in data
    assert len(data["agents"]) == 5


# ── Auth Tests ──

def test_unauthenticated_request_rejected():
    """Requests without auth token should return 401 or 403."""
    response = client.get("/tracker")
    # FastAPI's HTTPBearer returns 401 when no token is provided
    assert response.status_code in (401, 403)


def test_invalid_token_rejected():
    """Requests with invalid token should return 401."""
    response = client.get(
        "/tracker",
        headers={"Authorization": "Bearer totally-wrong-key"},
    )
    assert response.status_code == 401


def test_valid_api_key_accepted():
    """Requests with valid API key should be accepted."""
    response = client.get("/tracker", headers=AUTH_HEADERS)
    # Should return 200 (may have empty list or dict)
    assert response.status_code == 200


# ── Tracker Endpoints ──

def test_tracker_returns_data():
    """GET /tracker should return applications data."""
    response = client.get("/tracker", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    # API may return list or dict with 'applications' key
    assert isinstance(data, (list, dict))


def test_tracker_status_update_invalid_id():
    """PATCH /tracker/{id}/status with invalid ID should handle gracefully."""
    response = client.patch(
        "/tracker/nonexistent-id/status",
        json={"status": "interviewing"},
        headers=AUTH_HEADERS,
    )
    # Should either return 200, 404, or 422 (validation)
    assert response.status_code in (200, 404, 422)


# ── Job Search Endpoint ──

@patch("tools.searcher.search_jobs_structured")
def test_search_jobs(mock_search):
    """POST /jobs/search should return structured results."""
    mock_search.return_value = [
        {
            "title": "AI Engineer at TechCorp",
            "url": "https://example.com/job/1",
            "snippet": "Build AI systems...",
            "source": "linkedin",
        }
    ]

    response = client.post(
        "/jobs/search",
        json={"query": "AI engineer", "location": "remote"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data


def test_search_jobs_empty_query():
    """POST /jobs/search with empty query should process or reject."""
    response = client.post(
        "/jobs/search",
        json={"query": ""},
        headers=AUTH_HEADERS,
    )
    # Either returns empty results or validation error
    assert response.status_code in (200, 422)


# ── Run Endpoint ──

def test_run_requires_auth():
    """POST /run requires authentication."""
    response = client.post(
        "/run",
        json={"job_url": "https://example.com/job"},
    )
    # HTTPBearer returns 401 when no token provided
    assert response.status_code in (401, 403)


# ── Generate PDF Endpoint ──

@patch("tools.pdf_generator.generate_resume_pdf")
def test_generate_pdf(mock_pdf):
    """POST /generate-pdf should generate a PDF and return filepath."""
    mock_pdf.return_value = "./workspace/Resume_TechCorp_Engineer.pdf"

    response = client.post(
        "/generate-pdf",
        params={
            "name": "John Doe",
            "job_title": "AI Engineer",
            "company": "TechCorp",
            "tailored_bullets": "Built AI systems",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    data = response.json()
    assert "filepath" in data


# ── Download Endpoint ──

def test_download_nonexistent_file():
    """GET /download/{file} with nonexistent file should return 404."""
    response = client.get(
        "/download/nonexistent_file.pdf",
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404


def test_download_path_traversal():
    """GET /download with path traversal should be blocked."""
    response = client.get(
        "/download/..%2F..%2Fetc%2Fpasswd",
        headers=AUTH_HEADERS,
    )
    # Should be blocked — either 403 (access denied) or 404 (not found)
    assert response.status_code in (403, 404)
