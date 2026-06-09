"""
/metrics — Public health and version endpoints.

No authentication required; intended for uptime monitors, CI smoke tests,
and acquisition due-diligence dashboards.
"""
import os

from fastapi import APIRouter

router = APIRouter(prefix="/metrics", tags=["metrics"])

VERSION = "0.9.0"


@router.get("/version")
def get_version():
    """Return the application version and current git SHA."""
    return {
        "version": VERSION,
        "git_sha": os.environ.get("GIT_SHA", "unknown"),
    }


@router.get("/health")
def get_health():
    """
    Extended health check.

    Probes each external dependency and reports individual status.
    Returns HTTP 200 regardless — callers inspect the per-component
    ``status`` fields to determine degradation.
    """
    results: dict = {
        "status": "ok",
        "version": VERSION,
        "components": {},
    }

    # --- Supabase DB --------------------------------------------------------
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if supabase_url and supabase_key:
        try:
            from supabase import create_client
            client = create_client(supabase_url, supabase_key)
            client.table("profiles").select("id").limit(1).execute()
            results["components"]["supabase"] = "ok"
        except Exception as exc:
            results["components"]["supabase"] = f"error: {exc}"
            results["status"] = "degraded"
    else:
        results["components"]["supabase"] = "not_configured"

    # --- Supabase Storage ---------------------------------------------------
    storage_bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "videos")
    if supabase_url and supabase_key:
        try:
            from supabase import create_client
            client = create_client(supabase_url, supabase_key)
            client.storage.list_buckets()
            results["components"]["storage"] = "ok"
        except Exception as exc:
            results["components"]["storage"] = f"error: {exc}"
            results["status"] = "degraded"
    else:
        results["components"]["storage"] = "not_configured"

    # --- Anthropic API key present (not called — just check env) -----------
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    results["components"]["anthropic_api_key"] = (
        "configured" if anthropic_key else "not_configured"
    )

    # --- Stripe key present -------------------------------------------------
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    results["components"]["stripe"] = (
        "configured" if stripe_key else "not_configured"
    )

    return results
