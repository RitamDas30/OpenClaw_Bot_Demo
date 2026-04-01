#!/usr/bin/env python3
"""Shared GitHub API helpers for GitHub Spy scripts.

Design goals:
- lightweight stdlib-only implementation
- strict username validation
- consistent errors (no sys.exit in library functions)
- ETag cache to reduce API calls and improve speed
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

GITHUB_API = "https://api.github.com"
CACHE_DIR = Path.home() / ".openclaw" / "github-spy" / "cache"
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


def _load_token() -> str:
    """Resolve GitHub token with lightweight fallbacks."""
    env_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_token:
        return env_token

    token_file = Path.home() / ".openclaw" / "github-spy" / "github_token.txt"
    if token_file.exists():
        try:
            file_token = token_file.read_text().strip()
        except OSError:
            file_token = ""
        if file_token:
            return file_token

    cfg_file = Path.home() / ".openclaw" / "openclaw.json"
    if cfg_file.exists():
        try:
            cfg = json.loads(cfg_file.read_text())
        except (OSError, json.JSONDecodeError):
            cfg = {}
        config_token = str((cfg.get("env") or {}).get("GITHUB_TOKEN") or "").strip()
        if config_token:
            return config_token
    return ""


TOKEN = _load_token()


class GitHubApiError(RuntimeError):
    """Raised for non-404 API failures and transport errors."""


def parse_username(raw: str) -> str:
    """Extract and validate a GitHub username from text or URL."""
    if not raw or not raw.strip():
        raise ValueError("No GitHub username provided.")

    raw = raw.strip()
    match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([^/?#\s]+)", raw, re.IGNORECASE)
    if match:
        candidate = match.group(1)
    else:
        candidate = raw.lstrip("@").split()[0]

    candidate = candidate.strip()
    if not USERNAME_RE.match(candidate):
        raise ValueError(f"Invalid GitHub username format: '{candidate}'.")
    return candidate


def _cache_path(username: str, endpoint: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_endpoint = endpoint.replace("/", "_")
    return CACHE_DIR / f"{username}_{safe_endpoint}.json"


def api_get(path: str, etag: str | None = None, timeout: int = 12) -> tuple[int, dict | list | None, str | None]:
    """Raw GitHub GET with optional ETag support.

    Returns: (http_status, data_or_none, response_etag_or_none)
    """
    url = f"{GITHUB_API}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "OpenClaw-GitHubSpy/3.0")
    if TOKEN:
        req.add_header("Authorization", f"token {TOKEN}")
    if etag:
        req.add_header("If-None-Match", etag)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return 200, data, resp.headers.get("ETag")
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return 304, None, etag
        if exc.code == 404:
            return 404, None, None
        if exc.code == 403:
            raise GitHubApiError("GitHub API rate limit exceeded.")
        raise GitHubApiError(f"GitHub API {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise GitHubApiError(f"Cannot reach GitHub API: {exc.reason}") from exc


def api_get_cached(path: str, username: str, endpoint_name: str) -> dict | list | None:
    """GitHub GET with on-disk ETag cache; returns None only for 404."""
    cache_file = _cache_path(username, endpoint_name)
    cached_data: dict = {}
    if cache_file.exists():
        try:
            cached_data = json.loads(cache_file.read_text())
        except json.JSONDecodeError:
            cached_data = {}

    status, data, etag = api_get(path, etag=cached_data.get("etag"))
    if status == 404:
        return None
    if status == 304:
        return cached_data.get("data")

    cache_file.write_text(json.dumps({"etag": etag, "data": data}))
    return data


def fetch_user_parallel(username: str) -> tuple[dict | None, list, list]:
    """Fetch profile, repos, and recent public events in parallel."""
    endpoints = {
        "profile": f"/users/{username}",
        "repos": f"/users/{username}/repos?sort=pushed&per_page=100",
        "events": f"/users/{username}/events/public?per_page=100",
    }

    results: dict[str, dict | list | None] = {"profile": None, "repos": [], "events": []}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(api_get_cached, path, username, key): key for key, path in endpoints.items()
        }
        for future in futures:
            key = futures[future]
            results[key] = future.result()

    profile = results["profile"] if isinstance(results["profile"], dict) else None
    repos = results["repos"] if isinstance(results["repos"], list) else []
    events = results["events"] if isinstance(results["events"], list) else []
    return profile, repos, events


def fetch_profile(username: str) -> dict | None:
    """Fetch only profile data for fastest existence checks."""
    data = api_get_cached(f"/users/{username}", username, "profile")
    return data if isinstance(data, dict) else None


def fetch_profile_events(username: str) -> tuple[dict | None, list]:
    """Fetch only profile + events for lightweight spy reports."""
    endpoints = {
        "profile": f"/users/{username}",
        "events": f"/users/{username}/events/public?per_page=100",
    }

    results: dict[str, dict | list | None] = {"profile": None, "events": []}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(api_get_cached, path, username, key): key for key, path in endpoints.items()
        }
        for future in futures:
            key = futures[future]
            results[key] = future.result()

    profile = results["profile"] if isinstance(results["profile"], dict) else None
    events = results["events"] if isinstance(results["events"], list) else []
    return profile, events


def fetch_user(username: str) -> tuple[dict | None, list, list]:
    """Backward-compatible alias used by older scripts."""
    return fetch_user_parallel(username)


def analyze_developer(repos: list, events: list) -> dict:
    """Build reusable aggregate stats from repository data."""
    del events  # events currently unused in this aggregation
    original = [repo for repo in repos if not repo.get("fork")]
    forks = [repo for repo in repos if repo.get("fork")]

    langs: dict[str, int] = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1

    return {
        "total_stars": sum(repo.get("stargazers_count", 0) for repo in repos),
        "original_count": len(original),
        "fork_count": len(forks),
        "sorted_langs": sorted(langs.items(), key=lambda item: -item[1]),
        "original_repos": original,
    }
