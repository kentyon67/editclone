"""
Backend integration tests — API surface checks.

These tests run without a real database; they only verify routing,
auth enforcement, and response shapes.
"""
import pytest
from fastapi.testclient import TestClient


class TestHealth:
    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_body(self, client: TestClient):
        body = client.get("/health").json()
        assert body.get("status") == "ok"
        assert "version" in body


class TestAuthEnforcement:
    """Protected endpoints must return 401 when called without credentials."""

    def test_upload_without_auth_returns_401(self, client: TestClient):
        # POST with no Authorization header — multipart body not needed to hit auth check
        response = client.post("/videos/upload")
        assert response.status_code == 401

    def test_job_nonexistent_without_auth_returns_401(self, client: TestClient):
        response = client.get("/jobs/nonexistent-job-id")
        assert response.status_code == 401

    def test_plugin_me_without_auth_returns_401(self, client: TestClient):
        response = client.get("/plugin/me")
        assert response.status_code == 401


class TestCORS:
    """CORS preflight requests should return appropriate headers."""

    def test_options_request_returns_cors_headers(self, client: TestClient):
        response = client.options(
            "/health",
            headers={
                "Origin": "https://editclone.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI/Starlette returns 200 for OPTIONS on CORS middleware
        assert response.status_code in (200, 204)
        # Access-Control-Allow-Origin must be present
        assert "access-control-allow-origin" in response.headers


class TestMetrics:
    def test_version_endpoint(self, client: TestClient):
        response = client.get("/metrics/version")
        assert response.status_code == 200
        body = response.json()
        assert "version" in body
        assert "git_sha" in body

    def test_health_extended_endpoint_exists(self, client: TestClient):
        response = client.get("/metrics/health")
        # Returns 200 even when external services are unavailable
        assert response.status_code == 200
        body = response.json()
        assert "status" in body
