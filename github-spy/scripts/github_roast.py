#!/usr/bin/env python3
"""Fetch GitHub profile + repos data for roasting. Uses only stdlib."""

import sys
from github_api import fetch_user, parse_username


def main():
    if len(sys.argv) < 2:
        print("ERROR: No username provided. Usage: github_roast.py <username>")
        sys.exit(1)

    username = parse_username(sys.argv[1])
    profile, repos, _ = fetch_user(username)

    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    lang_str = ", ".join(
        f"{l} ({c})" for l, c in sorted(langs.items(), key=lambda x: -x[1])[:8]
    )

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

    print(f"=== ROAST DATA FOR @{username} ===")
    print(f"Name: {name}")
    print(f"Bio: {profile.get('bio') or 'No bio'}")
    print(f"Account created: {profile.get('created_at', '')[:10]}")
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
