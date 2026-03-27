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
        ammo.append(f"ONE-LANGUAGE LOYALIST: Only uses {lang}. Every single repo is {lang}.")
    elif len(sorted_langs) >= 8:
        ammo.append(f"LANGUAGE HOARDER: Uses {len(sorted_langs)} different languages. Jack of all trades, master of none.")
    elif sorted_langs and sorted_langs[0][1] >= len(repos) * 0.7 and len(repos) > 3:
        lang = sorted_langs[0][0]
        ammo.append(f"LANGUAGE OBSESSION: {sorted_langs[0][1]} out of {len(repos)} repos are {lang}.")

    # --- Fork ratio ---
    if len(forks) > len(original) and len(forks) > 3:
        ammo.append(f"FORK FARMER: {len(forks)} forks vs {len(original)} original repos. More forking than creating.")
    elif len(forks) >= len(original) and len(forks) > 2:
        ammo.append(f"FORK ADDICT: {len(forks)} forks, {len(original)} original. 50/50 split between own work and copy-paste.")
    elif len(forks) > 0 and len(original) == 0:
        ammo.append(f"ZERO ORIGINAL WORK: All {len(forks)} repos are forks. Not a single original thought.")

    # --- Star poverty ---
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    if total_stars == 0 and len(repos) > 3:
        ammo.append(f"ZERO STARS: {len(repos)} repos and not a single star. Even bots get more love.")
    elif total_stars < 5 and len(repos) > 10:
        ammo.append(f"STAR DROUGHT: {len(repos)} repos, only {total_stars} total stars.")

    # --- Follower/following ratio ---
    followers = profile.get("followers", 0)
    following = profile.get("following", 0)
    if following > 0 and followers == 0:
        ammo.append(f"FOLLOWING {following} PEOPLE, 0 FOLLOW BACK. Invisible on GitHub.")
    elif following > followers * 5 and following > 50:
        ammo.append(f"DESPERATE RATIO: Following {following} but only {followers} follow back.")
    elif followers > 1000 and following == 0:
        ammo.append(f"CELEBRITY COMPLEX: {followers} followers, following 0. Too important to follow back.")
    elif followers < 5 and len(repos) > 10:
        ammo.append(f"INVISIBLE: {len(repos)} repos but only {followers} followers. Nobody cares.")

    # --- README warriors / empty repos ---
    empty_repos = []
    readme_only = []
    for r in original:
        size = r.get("size", 0)
        if size == 0:
            empty_repos.append(r["name"])
        elif size < 5:
            readme_only.append(r["name"])
    if empty_repos:
        names = ", ".join(empty_repos[:5])
        ammo.append(f"GHOST REPOS: {len(empty_repos)} completely empty repos ({names}).")
    if readme_only:
        names = ", ".join(readme_only[:5])
        ammo.append(f"README WARRIOR: {len(readme_only)} repos that are just README files ({names}).")

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
    if stale:
        names = ", ".join(stale[:5])
        ammo.append(f"PROJECT GRAVEYARD: {len(stale)} repos untouched for 1+ year ({names}).")

    # --- Tutorial/clone repos ---
    tutorial_keywords = ["tutorial", "follow-along", "course", "udemy", "learn", "practice", "exercise", "bootcamp", "clone", "copy", "demo", "sample", "example"]
    tutorial_repos = [r["name"] for r in original if any(kw in (r.get("name") or "").lower() or kw in (r.get("description") or "").lower() for kw in tutorial_keywords)]
    if tutorial_repos:
        names = ", ".join(tutorial_repos[:5])
        ammo.append(f"TUTORIAL COLLECTOR: {len(tutorial_repos)} tutorial/demo repos ({names}). Learning, never building.")

    # --- No bio ---
    if not profile.get("bio"):
        ammo.append("NO BIO: Can't even write one line about themselves.")

    # --- Old account, low output ---
    created = profile.get("created_at", "")
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            years = (now.year - created_dt.year)
            if years >= 5 and len(original) < 5:
                ammo.append(f"VETERAN GHOST: Account is {years} years old but only {len(original)} original repos.")
            elif years >= 3 and total_stars == 0:
                ammo.append(f"{years} YEARS ON GITHUB, ZERO STARS. What have they been doing?")
        except (ValueError, TypeError):
            pass

    # --- Commit frequency ---
    push_events = [e for e in events if e.get("type") == "PushEvent"]
    total_commits = sum(len(e.get("payload", {}).get("commits", [])) for e in push_events)
    if len(events) > 0 and total_commits == 0:
        ammo.append("ZERO COMMITS in recent activity. Ghost.")
    elif total_commits > 200:
        ammo.append(f"COMMIT MACHINE: {total_commits} recent commits. God or just 'fix typo' 200 times.")

    # --- Repo naming ---
    numbered = [r["name"] for r in original if any(r["name"].endswith(str(i)) for i in range(1, 10)) or "-v2" in r["name"] or "-v3" in r["name"]]
    if len(numbered) >= 2:
        names = ", ".join(numbered[:4])
        ammo.append(f"VERSION HELL: Repos like {names}. Makes a new repo instead of updating.")

    # --- DSA grinder ---
    dsa_keywords = ["leetcode", "dsa", "competitive", "hackerrank", "codeforces", "algorithm", "data-structure", "cp-", "problem"]
    dsa_repos = [r["name"] for r in original if any(kw in (r.get("name") or "").lower() or kw in (r.get("description") or "").lower() for kw in dsa_keywords)]
    if dsa_repos and len(original) - len(dsa_repos) < 3:
        ammo.append(f"DSA GRINDER, NO PROJECTS: All competitive programming ({', '.join(dsa_repos[:3])}). Solved 500 problems, can't build an app.")

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

    total_stars = sum(r.get("stargazers_count", 0) for r in repos)

    # ALL repos with full details (not just top 8)
    repo_details = []
    for r in sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True):
        desc = r.get("description") or "no description"
        stars = r.get("stargazers_count", 0)
        fork = " [FORK]" if r.get("fork") else ""
        lang = r.get("language") or "?"
        size = r.get("size", 0)
        topics = r.get("topics", [])
        pushed = r.get("pushed_at", "")[:10]
        size_label = "empty" if size == 0 else f"{size}KB"
        topic_str = f" topics: {', '.join(topics)}" if topics else ""
        repo_details.append(
            f"  - {r['name']}: \"{desc}\" [{lang}, {stars}★, {size_label}, last push: {pushed}]{fork}{topic_str}"
        )

    # Silly/funny descriptions
    silly_descs = []
    for r in repos:
        desc = r.get("description") or ""
        if desc and len(desc) < 50 and any(c in desc.lower() for c in ["hehe", "lol", "blah", "test", "idk", "todo", "wip", "coming soon", "nothing", "just", "random", "bruh", "😂", "🚀", "💀"]):
            silly_descs.append(f'  - {r["name"]}: "{desc}"')
        elif desc and desc.strip().lower() in ["no description", ".", "..", "hi", "hello", "test", "asdf"]:
            silly_descs.append(f'  - {r["name"]}: "{desc}"')

    # Repos with no description at all
    no_desc_repos = [r["name"] for r in repos if not r.get("description")]

    # Recent commit messages from events (find funny/lazy ones)
    commit_msgs = []
    for e in events:
        if e.get("type") == "PushEvent":
            for c in e.get("payload", {}).get("commits", []):
                msg = c.get("message", "").split("\n")[0][:80]
                commit_msgs.append(msg)

    # Find lazy/funny commit messages
    lazy_commits = []
    lazy_keywords = ["fix", "update", "test", "wip", "initial commit", "first commit", "asdf", ".", "..", "idk", "stuff", "changes", "misc", "tmp", "todo", "oops", "typo", "lol", "bruh"]
    for msg in commit_msgs:
        if msg.lower().strip() in lazy_keywords or len(msg) < 4:
            lazy_commits.append(f'  - "{msg}"')
        elif any(kw == msg.lower().strip() for kw in lazy_keywords):
            lazy_commits.append(f'  - "{msg}"')
    # Also grab any particularly funny ones
    for msg in commit_msgs:
        if any(w in msg.lower() for w in ["hehe", "blah", "lol", "bruh", "😂", "💀", "please work", "why", "help", "idk", "fuck", "shit"]):
            entry = f'  - "{msg}"'
            if entry not in lazy_commits:
                lazy_commits.append(entry)

    # Detect roastable patterns
    ammo = detect_roast_ammo(profile, repos, events)

    # === OUTPUT ===
    print(f"=== ROAST TARGET: {name} (@{username}) ===")
    print(f"Real name: {name}")
    print(f"Bio: {profile.get('bio') or '[NO BIO]'}")
    print(f"Account created: {profile.get('created_at', '')[:10]}")
    print(f"Public repos: {profile.get('public_repos', 0)} ({len(original)} original, {len(forks)} forks)")
    print(f"Total stars: {total_stars}")
    print(f"Followers: {profile.get('followers', 0)} | Following: {profile.get('following', 0)}")
    print(f"Company: {profile.get('company') or '[None]'}")
    print(f"Location: {profile.get('location') or '[Unknown]'}")
    print(f"Languages: {lang_str or '[None]'}")
    print()

    print("ALL REPOS (with details):")
    for line in repo_details[:15]:
        print(line)
    if len(repo_details) > 15:
        print(f"  ... and {len(repo_details) - 15} more")
    print()

    if no_desc_repos:
        print(f"REPOS WITH NO DESCRIPTION ({len(no_desc_repos)}):")
        print(f"  {', '.join(no_desc_repos[:10])}")
        print()

    if silly_descs:
        print("SILLY/FUNNY DESCRIPTIONS (roast these!):")
        for s in silly_descs[:5]:
            print(s)
        print()

    if lazy_commits:
        print("LAZY/FUNNY COMMIT MESSAGES (roast these!):")
        for c in lazy_commits[:8]:
            print(c)
        print()

    if commit_msgs:
        print(f"RECENT COMMIT MESSAGES (sample of {min(len(commit_msgs), 10)}):")
        for msg in commit_msgs[:10]:
            print(f'  - "{msg}"')
        print()

    print("ROAST AMMUNITION:")
    for i, a in enumerate(ammo, 1):
        print(f"  {i}. {a}")
    if not ammo:
        print("  No specific weaknesses found. Roast the blandness itself.")
    print()

    print("=== ROAST INSTRUCTIONS ===")
    print(f"DESTROY {name} (@{username}). Absolutely BRUTAL roast. No mercy. No kindness.")
    print(f"")
    print(f"STRUCTURE:")
    print(f"  1. '{name} — [one-liner that destroys their identity]'")
    print(f"  2. Mock their WORST repos BY NAME. Quote silly descriptions WORD FOR WORD.")
    print(f"  3. Destroy stats: {total_stars} stars / {len(repos)} repos = {total_stars/max(len(repos),1):.2f} stars per repo. {profile.get('followers',0)} followers. Ratio math.")
    print(f"  4. Each AMMUNITION point above becomes its own punchline.")
    print(f"  5. Quote any silly descriptions or lazy commits directly.")
    print(f"  6. 'Verdict:' — sounds like compliment, is actually an insult.")
    print(f"")
    print(f"BANNED: 'impressive', 'keep it up', 'respect', 'not gonna lie', any encouragement.")
    print(f"TONE: Talk DOWN to them. You are JUDGING from above. Dominant, not whiny.")
    print(f"LENGTH: 200-300 words. Punchline after punchline. No filler.")
    print(f"ONLY use data from above. Never make up repos or stats.")


if __name__ == "__main__":
    main()
