#!/usr/bin/env python3
"""Shared GitHub API client with caching. Uses only stdlib."""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
CACHE_DIR = Path.home() / ".openclaw" / "github-spy" / "cache"
CACHE_TTL = 300  # 5 minutes


def api_get(path: str) -> dict | list | None:
    url = f"{GITHUB_API}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "OpenClaw-GitHubSpy/1.0")
    if TOKEN:
        req.add_header("Authorization", f"token {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code == 403:
            print("ERROR: GitHub API rate limit exceeded. Try again later or set GITHUB_TOKEN for 5000 req/hr.")
            sys.exit(1)
        if e.code == 401:
            print("ERROR: GITHUB_TOKEN is invalid. Check your token or unset it.")
            sys.exit(1)
        print(f"ERROR: GitHub API returned {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot reach GitHub API. Check your internet connection. ({e.reason})")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected failure: {e}")
        return None


def _cache_key(username: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{username}.json"


def _load_cache(username: str) -> dict | None:
    path = _cache_key(username)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("ts", 0) < CACHE_TTL:
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _save_cache(username: str, profile: dict, repos: list, events: list):
    path = _cache_key(username)
    path.write_text(json.dumps({
        "ts": time.time(),
        "profile": profile,
        "repos": repos,
        "events": events,
    }))


def fetch_user(username: str) -> tuple[dict, list, list]:
    """Fetch profile, repos, events with 5-min cache. Returns (profile, repos, events)."""
    cached = _load_cache(username)
    if cached:
        return cached["profile"], cached["repos"], cached["events"]

    profile = api_get(f"/users/{username}")
    if not profile:
        print(f"ERROR: GitHub user '{username}' does not exist. Double-check the spelling.")
        sys.exit(1)

    repos = api_get(f"/users/{username}/repos?sort=pushed&per_page=100") or []
    events = api_get(f"/users/{username}/events/public?per_page=100") or []

    _save_cache(username, profile, repos, events)
    return profile, repos, events


def parse_username(raw: str) -> str:
    """Extract username from various formats: URL, @mention, plain text."""
    raw = raw.strip()
    # Handle GitHub URLs
    for prefix in ["https://github.com/", "http://github.com/", "github.com/"]:
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix):]
            break
    # Strip trailing slashes and paths
    raw = raw.split("/")[0].split("?")[0]
    # Strip @ prefix
    raw = raw.lstrip("@")
    if not raw:
        print("ERROR: No username provided.")
        sys.exit(1)
    return raw
