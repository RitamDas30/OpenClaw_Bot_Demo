#!/usr/bin/env python3
"""Fetch GitHub profile and generate a skill/project summary. Uses only stdlib."""

import sys
from datetime import datetime
from github_api import GitHubApiError, fetch_user, parse_username


def classify_repo(repo: dict) -> str:
    name = (repo.get("name") or "").lower()
    desc = (repo.get("description") or "").lower()
    topics = [t.lower() for t in repo.get("topics", [])]
    combined = f"{name} {desc} {' '.join(topics)}"

    categories = [
        ("Web/Frontend", ["web", "frontend", "react", "vue", "angular", "nextjs", "html", "css", "tailwind"]),
        ("Backend/API", ["api", "backend", "server", "rest", "graphql", "fastapi", "express", "django", "flask"]),
        ("AI/ML", ["ml", "machine-learning", "deep-learning", "ai", "neural", "tensorflow", "pytorch", "llm"]),
        ("Data Science", ["data", "analytics", "pandas", "jupyter", "notebook", "visualization"]),
        ("Mobile", ["mobile", "android", "ios", "flutter", "react-native", "swift", "kotlin"]),
        ("DevOps/Infra", ["devops", "docker", "kubernetes", "ci", "cd", "terraform", "ansible", "deploy"]),
        ("Tools/CLI", ["cli", "tool", "utility", "script", "automation", "bot"]),
        ("Game Dev", ["game", "unity", "godot", "pygame"]),
        ("Security", ["security", "crypto", "hack", "ctf", "pentest"]),
        ("Library/Framework", ["lib", "library", "package", "sdk", "framework", "module"]),
    ]
    for cat, keywords in categories:
        if any(w in combined for w in keywords):
            return cat
    if (repo.get("language") or "").lower() in ["jupyter notebook", "r"]:
        return "Data Science"
    return "Other"


def main():
    if len(sys.argv) < 2:
        print("ERROR: No username provided. Usage: github_summarize.py <username>")
        sys.exit(1)

    try:
        username = parse_username(sys.argv[1])
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    try:
        profile, repos, events = fetch_user(username)
    except GitHubApiError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    if not profile:
        print(f"ERROR: GitHub user '{username}' not found.")
        sys.exit(1)

    # Languages
    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    sorted_langs = sorted(langs.items(), key=lambda x: -x[1])
    primary_langs = [l for l, _ in sorted_langs[:3]]
    all_langs = [f"{l} ({c} repos)" for l, c in sorted_langs[:10]]

    # Project categories
    categories = {}
    original_repos = [r for r in repos if not r.get("fork")]
    for r in original_repos:
        cat = classify_repo(r)
        categories[cat] = categories.get(cat, 0) + 1
    sorted_cats = sorted(categories.items(), key=lambda x: -x[1])

    # Stats
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    forked_repos = [r for r in repos if r.get("fork")]

    # Top projects
    top_repos = sorted(original_repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:5]
    top_lines = []
    for r in top_repos:
        desc = (r.get("description") or "no description")[:50]
        stars = r.get("stargazers_count", 0)
        lang = r.get("language") or "?"
        top_lines.append(f"  - {r['name']}: {desc} [{lang}, {stars} stars]")

    # Commit frequency from events
    push_events = [e for e in events if e.get("type") == "PushEvent"]
    total_commits = sum(len(e.get("payload", {}).get("commits", [])) for e in push_events)
    active_dates = {e.get("created_at", "")[:10] for e in events if e.get("created_at")}

    # Skill signals
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
    now_year = str(datetime.now().year)
    if any(r.get("pushed_at", "")[:4] == now_year for r in repos):
        skill_signals.append(f"actively coding in {now_year}")

    name = profile.get("name") or profile["login"]

    print(f"=== DEVELOPER PROFILE: @{username} ===")
    print(f"Name: {name}")
    print(f"Bio: {profile.get('bio') or 'No bio'}")
    print(f"Location: {profile.get('location') or 'Unknown'}")
    print(f"Company: {profile.get('company') or 'None'}")
    print(f"GitHub since: {profile.get('created_at', '')[:10]}")
    print(f"Followers: {profile.get('followers', 0)} | Following: {profile.get('following', 0)}")
    print()
    print(f"STATS:")
    print(f"  Repos: {profile.get('public_repos', 0)} ({len(original_repos)} original, {len(forked_repos)} forks)")
    print(f"  Total stars: {total_stars}")
    print(f"  Recent commits: {total_commits} (from last ~90 days of public events)")
    print(f"  Active days (recent): {len(active_dates)}")
    print()
    print(f"LANGUAGES: {', '.join(all_langs) if all_langs else 'None'}")
    print(f"Primary stack: {', '.join(primary_langs) if primary_langs else 'Unknown'}")
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
