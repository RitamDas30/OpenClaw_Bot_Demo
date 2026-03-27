#!/usr/bin/env python3
"""Fetch GitHub profile + repos data for roasting. Uses only stdlib."""

import json
import os
import sys
import urllib.request
import urllib.error

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


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
            print("ERROR: GITHUB_TOKEN is invalid. Check your token or unset it to use unauthenticated access.")
            sys.exit(1)
        print(f"ERROR: GitHub API returned {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot reach GitHub API. Check your internet connection. ({e.reason})")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected failure: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("ERROR: No username provided. Usage: github_roast.py <username>")
        sys.exit(1)

    username = sys.argv[1].strip().lstrip("@")
    if not username or "/" in username:
        print(f"ERROR: '{sys.argv[1]}' is not a valid GitHub username.")
        sys.exit(1)

    profile = api_get(f"/users/{username}")
    if not profile:
        print(f"ERROR: GitHub user '{username}' does not exist. Double-check the spelling.")
        sys.exit(1)

    repos = api_get(f"/users/{username}/repos?sort=pushed&per_page=30") or []

    # Language breakdown
    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    lang_str = ", ".join(
        f"{l} ({c})" for l, c in sorted(langs.items(), key=lambda x: -x[1])[:8]
    )

    # Top repos by stars
    sorted_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)
    repo_lines = []
    for r in sorted_repos[:10]:
        desc = (r.get("description") or "no description")[:60]
        stars = r.get("stargazers_count", 0)
        fork = " (FORK)" if r.get("fork") else ""
        lang = r.get("language") or "?"
        repo_lines.append(f"  - {r['name']}: {desc} [{lang}, {stars} stars]{fork}")

    fork_count = sum(1 for r in repos if r.get("fork"))

    name = profile.get("name") or profile["login"]
    bio = profile.get("bio") or "No bio"
    created = profile.get("created_at", "")[:10]

    print(f"=== ROAST DATA FOR @{username} ===")
    print(f"Name: {name}")
    print(f"Username: {profile['login']}")
    print(f"Bio: {bio}")
    print(f"Account created: {created}")
    print(f"Public repos: {profile.get('public_repos', 0)} ({fork_count} are forks)")
    print(f"Followers: {profile.get('followers', 0)} | Following: {profile.get('following', 0)}")
    print(f"Company: {profile.get('company') or 'None'}")
    print(f"Location: {profile.get('location') or 'Unknown'}")
    print(f"Languages: {lang_str or 'None detected'}")
    print(f"\nTop repos:")
    print("\n".join(repo_lines) if repo_lines else "  No repos found")
    print(f"\n=== NOW ROAST THEM ===")


if __name__ == "__main__":
    main()
