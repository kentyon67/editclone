"""
Pytest configuration and shared fixtures for EditClone backend tests.
"""
import os
import pytest
from fastapi.testclient import TestClient

# Ensure auth is disabled during tests (no real Supabase needed)
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("ANTHROPIC_API_KEY", "")


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Return a TestClient for the FastAPI app."""
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


# Marker for tests that require real external credentials
needs_credentials = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL"),
    reason="Requires real SUPABASE_URL credential",
)
