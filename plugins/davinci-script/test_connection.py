#!/usr/bin/env python3
"""
EditClone — DaVinci Script Connection Tester
=============================================
Standalone test script. No DaVinci Resolve installation required.

Tests:
  1. Config file presence
  2. API health check (/health)
  3. Authentication (/plugin/me)
  4. Job listing (/plugin/jobs)

Usage:
  python test_connection.py
  python test_connection.py --api-url https://editclone-production.up.railway.app --token eck_xxx
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_PATH = Path.home() / ".editclone" / "config.json"
DEFAULT_API_URL = "https://editclone-production.up.railway.app"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _color(text: str, code: str) -> str:
    """ANSI color if stdout is a TTY."""
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text


def ok(msg: str) -> str:
    return _color(f"  PASS  {msg}", "32")  # green


def fail(msg: str) -> str:
    return _color(f"  FAIL  {msg}", "31")  # red


def warn(msg: str) -> str:
    return _color(f"  WARN  {msg}", "33")  # yellow


def info(msg: str) -> str:
    return _color(f"  INFO  {msg}", "36")  # cyan


def section(title: str) -> None:
    print()
    print(_color(f"--- {title} ---", "1"))  # bold


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> tuple[str, str]:
    """Return (api_url, api_token) from ~/.editclone/config.json."""
    if not CONFIG_PATH.exists():
        return "", ""
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data.get("api_url", ""), data.get("api_token", "")
    except Exception:
        return "", ""


def test_config(api_url: str, api_token: str) -> None:
    section("Config")
    if CONFIG_PATH.exists():
        print(ok(f"Config file found: {CONFIG_PATH}"))
    else:
        print(warn(f"Config file not found: {CONFIG_PATH}"))
        print(info(f"  Run the DaVinci script once to create it, or create manually:"))
        print(info(f'  mkdir -p ~/.editclone && echo \'{{"api_url":"{api_url}","api_token":"eck_YOUR_TOKEN"}}\' > ~/.editclone/config.json'))

    if api_url:
        print(ok(f"API URL: {api_url}"))
    else:
        print(fail("API URL is empty"))

    if api_token:
        masked = api_token[:6] + "..." if len(api_token) > 6 else "***"
        print(ok(f"Token:   {masked}"))
    else:
        print(fail("API token is empty"))
        print(info("  Get your token at: https://editclone.vercel.app/ja/account"))


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _request(method: str, url: str, token: str = "", payload: dict | None = None,
             timeout: int = 10) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        if token.startswith("eck_"):
            req.add_header("X-Api-Key", token)
        else:
            req.add_header("Authorization", f"Bearer {token}")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        return e.code, body
    except urllib.error.URLError as e:
        raise ConnectionError(str(e.reason)) from e


# ---------------------------------------------------------------------------
# Individual tests
# ---------------------------------------------------------------------------

def test_health(api_url: str) -> bool:
    section("Health Check  (GET /health)")
    url = f"{api_url}/health"
    print(info(f"  {url}"))
    try:
        status, body = _request("GET", url)
        if status == 200:
            version = body.get("version", "?")
            print(ok(f"HTTP {status} — version: {version}"))
            return True
        else:
            print(fail(f"HTTP {status}: {body}"))
            return False
    except ConnectionError as e:
        print(fail(f"Connection error: {e}"))
        print(info("  Check that the API URL is correct and the backend is running."))
        return False
    except Exception as e:
        print(fail(f"Unexpected error: {e}"))
        return False


def test_auth(api_url: str, token: str) -> bool:
    section("Authentication  (GET /plugin/me)")
    if not token:
        print(fail("No token — skipping auth test"))
        return False
    url = f"{api_url}/plugin/me"
    print(info(f"  {url}"))
    try:
        status, body = _request("GET", url, token=token)
        if status == 200:
            email = body.get("email", "unknown")
            plan  = body.get("plan", "?")
            print(ok(f"HTTP {status} — authenticated as: {email}  (plan: {plan})"))
            return True
        elif status == 401:
            print(fail(f"HTTP 401 — Unauthorized. Token may be invalid or expired."))
            print(info("  Regenerate your token at: https://editclone.vercel.app/ja/account"))
            return False
        elif status == 403:
            print(fail(f"HTTP 403 — Forbidden. Your plan may not include plugin access."))
            return False
        else:
            print(fail(f"HTTP {status}: {body}"))
            return False
    except ConnectionError as e:
        print(fail(f"Connection error: {e}"))
        return False
    except Exception as e:
        print(fail(f"Unexpected error: {e}"))
        return False


def test_jobs(api_url: str, token: str) -> bool:
    section("Job Listing  (GET /plugin/jobs)")
    if not token:
        print(fail("No token — skipping jobs test"))
        return False
    url = f"{api_url}/plugin/jobs"
    print(info(f"  {url}"))
    try:
        status, body = _request("GET", url, token=token)
        if status == 200:
            jobs = body.get("jobs", [])
            count = len(jobs)
            print(ok(f"HTTP {status} — {count} job(s) found"))
            if jobs:
                latest = jobs[0]
                name = latest.get("video_name") or latest.get("filename", "?")
                date = (latest.get("created_at") or "")[:10]
                print(info(f"  Latest: {name}  ({date})"))
            else:
                print(info("  No jobs yet. Upload a video at https://editclone.vercel.app"))
            return True
        elif status == 401:
            print(fail(f"HTTP 401 — Unauthorized"))
            return False
        else:
            print(fail(f"HTTP {status}: {body}"))
            return False
    except ConnectionError as e:
        print(fail(f"Connection error: {e}"))
        return False
    except Exception as e:
        print(fail(f"Unexpected error: {e}"))
        return False


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(results: dict[str, bool]) -> None:
    section("Summary")
    all_pass = True
    for name, passed in results.items():
        if passed:
            print(ok(name))
        else:
            print(fail(name))
            all_pass = False
    print()
    if all_pass:
        print(_color("All tests passed. The DaVinci plugin is ready to use.", "32;1"))
    else:
        print(_color("Some tests failed. See details above.", "31;1"))
        print()
        print("Troubleshooting:")
        print("  - Verify your API URL: https://editclone-production.up.railway.app")
        print("  - Get a fresh token: https://editclone.vercel.app/ja/account")
        print("  - Check Railway backend status: https://railway.app/dashboard")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test the EditClone API connection for the DaVinci Resolve plugin."
    )
    parser.add_argument(
        "--api-url",
        default="",
        help=f"API URL (default: from config or {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--token",
        default="",
        help="API token starting with eck_ (default: from config)",
    )
    args = parser.parse_args()

    print(_color("EditClone — Connection Test", "1;36"))
    print(_color("=" * 40, "36"))

    # Resolve config
    cfg_url, cfg_token = load_config()
    api_url = args.api_url or cfg_url or DEFAULT_API_URL
    token   = args.token   or cfg_token

    test_config(api_url, token)

    results = {
        "Config": bool(api_url and token),
        "Health (/health)":            test_health(api_url),
        "Auth (/plugin/me)":           test_auth(api_url, token),
        "Jobs (/plugin/jobs)":         test_jobs(api_url, token),
    }

    print_summary(results)
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
