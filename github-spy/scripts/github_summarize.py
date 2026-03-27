#!/usr/bin/env python3
"""Fetch GitHub profile and generate a skill/project summary. Uses only stdlib."""

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
            print("ERROR: GITHUB_TOKEN is invalid.")
            sys.exit(1)
        print(f"ERROR: GitHub API returned {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot reach GitHub API. Check your internet connection. ({e.reason})")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected failure: {e}")
        return None


def classify_repo(repo: dict) -> str:
    """Guess project category from repo metadata."""
    name = (repo.get("name") or "").lower()
    desc = (repo.get("description") or "").lower()
    lang = (repo.get("language") or "").lower()
    topics = [t.lower() for t in repo.get("topics", [])]
    combined = f"{name} {desc} {' '.join(topics)}"

    if any(w in combined for w in ["web", "frontend", "react", "vue", "angular", "nextjs", "html", "css", "tailwind"]):
        return "Web/Frontend"
    if any(w in combined for w in ["api", "backend", "server", "rest", "graphql", "fastapi", "express", "django", "flask"]):
        return "Backend/API"
    if any(w in combined for w in ["ml", "machine-learning", "deep-learning", "ai", "neural", "model", "tensorflow", "pytorch", "llm"]):
        return "AI/ML"
    if any(w in combined for w in ["data", "analytics", "pandas", "jupyter", "notebook", "visualization"]):
        return "Data Science"
    if any(w in combined for w in ["mobile", "android", "ios", "flutter", "react-native", "swift", "kotlin"]):
        return "Mobile"
    if any(w in combined for w in ["devops", "docker", "kubernetes", "ci", "cd", "terraform", "ansible", "deploy"]):
        return "DevOps/Infra"
    if any(w in combined for w in ["cli", "tool", "utility", "script", "automation", "bot"]):
        return "Tools/CLI"
    if any(w in combined for w in ["game", "unity", "godot", "pygame"]):
        return "Game Dev"
    if any(w in combined for w in ["security", "crypto", "hack", "ctf", "pentest"]):
        return "Security"
    if any(w in combined for w in ["lib", "library", "package", "sdk", "framework", "module"]):
        return "Library/Framework"
    if lang in ["jupyter notebook", "r"]:
        return "Data Science"
    return "Other"


def main():
    if len(sys.argv) < 2:
        print("ERROR: No username provided. Usage: github_summarize.py <username>")
        sys.exit(1)

    username = sys.argv[1].strip().lstrip("@")
    if not username or "/" in username:
        print(f"ERROR: '{sys.argv[1]}' is not a valid GitHub username.")
        sys.exit(1)

    profile = api_get(f"/users/{username}")
    if not profile:
        print(f"ERROR: GitHub user '{username}' does not exist. Double-check the spelling.")
        sys.exit(1)

    repos = api_get(f"/users/{username}/repos?sort=pushed&per_page=100") or []

    # --- Language breakdown ---
    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    sorted_langs = sorted(langs.items(), key=lambda x: -x[1])
    primary_langs = [l for l, _ in sorted_langs[:3]]
    all_langs = [f"{l} ({c} repos)" for l, c in sorted_langs[:10]]

    # --- Project categories ---
    categories = {}
    for r in repos:
        if not r.get("fork"):
            cat = classify_repo(r)
            categories[cat] = categories.get(cat, 0) + 1
    sorted_cats = sorted(categories.items(), key=lambda x: -x[1])

    # --- Stats ---
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    original_repos = [r for r in repos if not r.get("fork")]
    forked_repos = [r for r in repos if r.get("fork")]

    # --- Top projects (non-fork, by stars) ---
    top_repos = sorted(original_repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:5]
    top_lines = []
    for r in top_repos:
        desc = (r.get("description") or "no description")[:50]
        stars = r.get("stargazers_count", 0)
        lang = r.get("language") or "?"
        top_lines.append(f"  - {r['name']}: {desc} [{lang}, {stars} stars]")

    # --- Skill level guess ---
    skill_signals = []
    if profile.get("public_repos", 0) > 50:
        skill_signals.append("prolific (50+ repos)")
    if total_stars > 100:
        skill_signals.append(f"community recognition ({total_stars} total stars)")
    if len(langs) > 5:
        skill_signals.append(f"polyglot ({len(langs)} languages)")
    if any(r.get("stargazers_count", 0) > 1000 for r in repos):
        skill_signals.append("has viral project (1000+ stars)")
    if profile.get("followers", 0) > 100:
        skill_signals.append(f"influential ({profile['followers']} followers)")
    has_recent = any(r.get("pushed_at", "")[:4] == "2026" for r in repos)
    if has_recent:
        skill_signals.append("actively coding in 2026")

    # --- Output ---
    name = profile.get("name") or profile["login"]
    bio = profile.get("bio") or "No bio"
    created = profile.get("created_at", "")[:10]

    print(f"=== DEVELOPER PROFILE: @{username} ===")
    print(f"Name: {name}")
    print(f"Bio: {bio}")
    print(f"Location: {profile.get('location') or 'Unknown'}")
    print(f"Company: {profile.get('company') or 'None'}")
    print(f"GitHub since: {created}")
    print(f"Followers: {profile.get('followers', 0)} | Following: {profile.get('following', 0)}")
    print()
    print(f"STATS:")
    print(f"  Total repos: {profile.get('public_repos', 0)} ({len(original_repos)} original, {len(forked_repos)} forks)")
    print(f"  Total stars: {total_stars}")
    print()
    print(f"LANGUAGES (by repo count):")
    for l in all_langs:
        print(f"  {l}")
    print(f"  Primary stack: {', '.join(primary_langs) if primary_langs else 'Unknown'}")
    print()
    print(f"PROJECT DOMAINS:")
    for cat, count in sorted_cats:
        print(f"  {cat}: {count} repos")
    print()
    print(f"TOP PROJECTS:")
    print("\n".join(top_lines) if top_lines else "  No original repos found")
    print()
    print(f"SKILL SIGNALS:")
    for s in skill_signals:
        print(f"  - {s}")
    if not skill_signals:
        print("  - early stage / low public activity")
    print()
    print(f"=== SUMMARIZE THIS DEVELOPER'S PROFILE ===")


if __name__ == "__main__":
    main()
