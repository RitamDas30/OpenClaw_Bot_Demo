#!/usr/bin/env python3
"""Fetch GitHub profile + repos data and detect roastable patterns. Uses only stdlib."""

import sys
from datetime import datetime
from github_api import fetch_user, parse_username


def detect_roast_ammo(profile: dict, repos: list, events: list) -> list[str]:
    """Analyze the profile and return specific roastable observations."""
    ammo = []
    username = profile["login"]
    name = profile.get("name") or username
    original = [r for r in repos if not r.get("fork")]
    forks = [r for r in repos if r.get("fork")]

    # --- Language patterns ---
    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    sorted_langs = sorted(langs.items(), key=lambda x: -x[1])

    if len(sorted_langs) == 1:
        lang = sorted_langs[0][0]
        ammo.append(f"ONE-LANGUAGE LOYALIST: Only uses {lang}. Every single repo is {lang}. Monogamous with a programming language.")
    elif len(sorted_langs) >= 8:
        ammo.append(f"LANGUAGE HOARDER: Uses {len(sorted_langs)} different languages. Jack of all trades, master of none.")
    elif sorted_langs and sorted_langs[0][1] >= len(repos) * 0.7:
        lang = sorted_langs[0][0]
        ammo.append(f"LANGUAGE OBSESSION: {sorted_langs[0][1]} out of {len(repos)} repos are {lang}. Has a type.")

    # --- Fork ratio ---
    if len(forks) > len(original) and len(forks) > 3:
        ammo.append(f"FORK FARMER: {len(forks)} forks vs {len(original)} original repos. More forking than creating.")
    elif len(forks) > 0 and len(original) == 0:
        ammo.append(f"ZERO ORIGINAL WORK: All {len(forks)} repos are forks. Has never had an original thought on GitHub.")

    # --- Star poverty ---
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    if total_stars == 0 and len(repos) > 5:
        ammo.append(f"ZERO STARS: {len(repos)} repos and not a single star. Even bots have more recognition.")
    elif total_stars < 5 and len(repos) > 10:
        ammo.append(f"STAR DROUGHT: {len(repos)} repos, only {total_stars} total stars. The code is so mid even GitHub won't recommend it.")

    # --- Follower/following ratio ---
    followers = profile.get("followers", 0)
    following = profile.get("following", 0)
    if following > 0 and followers == 0:
        ammo.append(f"FOLLOWING {following} PEOPLE, 0 FOLLOW BACK: Networking level = invisible.")
    elif following > followers * 5 and following > 50:
        ammo.append(f"DESPERATE RATIO: Following {following} people but only {followers} follow back. GitHub isn't Instagram bro.")
    elif followers > 1000 and following == 0:
        ammo.append(f"CELEBRITY COMPLEX: {followers} followers, following 0 people. Too important to follow back.")

    # --- README warriors / empty repos ---
    empty_repos = []
    readme_only = []
    for r in original:
        size = r.get("size", 0)
        if size == 0:
            empty_repos.append(r["name"])
        elif size < 5:
            readme_only.append(r["name"])

    if len(empty_repos) >= 3:
        names = ", ".join(empty_repos[:4])
        ammo.append(f"GHOST REPOS: {len(empty_repos)} completely empty repos ({names}). Created them and ghosted.")
    if len(readme_only) >= 3:
        names = ", ".join(readme_only[:4])
        ammo.append(f"README WARRIOR: {len(readme_only)} repos that are basically just README files ({names}). The documentation is the product.")

    # --- Unfinished projects / graveyard ---
    now = datetime.now()
    stale = []
    for r in original:
        pushed = r.get("pushed_at", "")
        if pushed:
            try:
                dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
                days_ago = (now.astimezone() - dt).days if dt.tzinfo else (now - dt.replace(tzinfo=None)).days
                if days_ago > 365:
                    stale.append(r["name"])
            except (ValueError, TypeError):
                pass
    if len(stale) >= 5:
        names = ", ".join(stale[:4])
        ammo.append(f"PROJECT GRAVEYARD: {len(stale)} repos untouched for 1+ year ({names}...). Startup cemetery.")
    elif len(stale) >= 3:
        names = ", ".join(stale[:3])
        ammo.append(f"ABANDONMENT ISSUES: {len(stale)} abandoned repos ({names}). Starts everything, finishes nothing.")

    # --- Tutorial/clone repos ---
    tutorial_keywords = ["tutorial", "follow-along", "course", "udemy", "learn", "practice", "exercise", "bootcamp", "clone", "copy"]
    tutorial_repos = [r["name"] for r in original if any(kw in (r.get("name") or "").lower() or kw in (r.get("description") or "").lower() for kw in tutorial_keywords)]
    if len(tutorial_repos) >= 3:
        names = ", ".join(tutorial_repos[:4])
        ammo.append(f"TUTORIAL COLLECTOR: {len(tutorial_repos)} repos from tutorials/courses ({names}). Learning everything except how to build something original.")

    # --- No bio ---
    if not profile.get("bio"):
        ammo.append("NO BIO: Can't even describe themselves in one line. The mystery nobody asked for.")

    # --- Old account, low output ---
    created = profile.get("created_at", "")
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            years = (now.year - created_dt.year)
            if years >= 5 and len(original) < 5:
                ammo.append(f"VETERAN GHOST: Account is {years} years old but only {len(original)} original repos. What have they been doing?")
            elif years >= 3 and total_stars == 0:
                ammo.append(f"3+ YEARS, ZERO IMPACT: On GitHub since {created[:4]} with nothing to show for it.")
        except (ValueError, TypeError):
            pass

    # --- Commit frequency ---
    push_events = [e for e in events if e.get("type") == "PushEvent"]
    total_commits = sum(len(e.get("payload", {}).get("commits", [])) for e in push_events)
    if len(events) > 0 and total_commits == 0:
        ammo.append("ZERO COMMITS in recent activity. Ghost account vibes.")
    elif total_commits > 200:
        ammo.append(f"COMMIT MACHINE: {total_commits} commits in recent history. Either a god or just pushing 'fix typo' 200 times.")

    # --- Repo naming ---
    numbered = [r["name"] for r in original if any(r["name"].endswith(str(i)) for i in range(1, 10)) or "-v2" in r["name"] or "-v3" in r["name"]]
    if len(numbered) >= 3:
        names = ", ".join(numbered[:4])
        ammo.append(f"VERSION HELL: Repos like {names}. Can't update existing code, just makes a new repo every time.")

    # --- DSA grinder ---
    dsa_keywords = ["leetcode", "dsa", "competitive", "hackerrank", "codeforces", "algorithm", "data-structure", "cp-", "problem"]
    dsa_repos = [r["name"] for r in original if any(kw in (r.get("name") or "").lower() or kw in (r.get("description") or "").lower() for kw in dsa_keywords)]
    if len(dsa_repos) >= 2 and len(original) - len(dsa_repos) < 3:
        ammo.append(f"DSA GRINDER, NO PROJECTS: Repos are all competitive programming ({', '.join(dsa_repos[:3])}). Solved 500 problems but can't build an app.")

    # --- "Impressive but..." ---
    if total_stars > 500 and followers > 100:
        ammo.append(f"ACTUALLY IMPRESSIVE: {total_stars} stars, {followers} followers. Hard to roast... but how's the work-life balance?")

    return ammo


def main():
    if len(sys.argv) < 2:
        print("ERROR: No username provided. Usage: github_roast.py <username>")
        sys.exit(1)

    username = parse_username(sys.argv[1])
    profile, repos, events = fetch_user(username)

    name = profile.get("name") or profile["login"]
    original = [r for r in repos if not r.get("fork")]
    forks = [r for r in repos if r.get("fork")]

    # Languages
    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    lang_str = ", ".join(f"{l} ({c})" for l, c in sorted(langs.items(), key=lambda x: -x[1])[:8])

    # Top repos
    sorted_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)
    repo_lines = []
    for r in sorted_repos[:8]:
        desc = (r.get("description") or "no description")[:50]
        stars = r.get("stargazers_count", 0)
        fork = " (FORK)" if r.get("fork") else ""
        lang = r.get("language") or "?"
        repo_lines.append(f"  - {r['name']}: {desc} [{lang}, {stars} stars]{fork}")

    total_stars = sum(r.get("stargazers_count", 0) for r in repos)

    # Detect roastable patterns
    ammo = detect_roast_ammo(profile, repos, events)

    print(f"=== ROAST TARGET: {name} (@{username}) ===")
    print(f"Bio: {profile.get('bio') or 'No bio'}")
    print(f"Account: {profile.get('created_at', '')[:10]}")
    print(f"Repos: {profile.get('public_repos', 0)} ({len(original)} original, {len(forks)} forks)")
    print(f"Stars: {total_stars} | Followers: {profile.get('followers', 0)} | Following: {profile.get('following', 0)}")
    print(f"Company: {profile.get('company') or 'None'} | Location: {profile.get('location') or 'Unknown'}")
    print(f"Languages: {lang_str or 'None'}")
    print()
    print("REPOS:")
    print("\n".join(repo_lines) if repo_lines else "  No repos found")
    print()
    print("ROAST AMMUNITION (use these in the roast):")
    for i, a in enumerate(ammo, 1):
        print(f"  {i}. {a}")
    if not ammo:
        print("  Profile is too generic to find specific weaknesses. Roast the blandness itself.")
    print()
    print("=== INSTRUCTIONS ===")
    print(f"Write a brutal, personalized roast of {name} (@{username}).")
    print(f"START with their name. Use SPECIFIC repo names, languages, and stats from above.")
    print(f"Reference the ROAST AMMUNITION points. Be savage but funny. Max 100 words.")
    print(f"End with one backhanded compliment.")


if __name__ == "__main__":
    main()
