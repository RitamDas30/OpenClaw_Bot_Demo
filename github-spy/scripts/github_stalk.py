#!/usr/bin/env python3
"""Fetch GitHub activity data for surveillance report. Uses only stdlib."""

import sys
from datetime import datetime
from github_api import fetch_user, parse_username


def main():
    if len(sys.argv) < 2:
        print("ERROR: No username provided. Usage: github_stalk.py <username>")
        sys.exit(1)

    username = parse_username(sys.argv[1])
    profile, repos, events = fetch_user(username)

    # Active hours analysis
    hour_buckets = {}
    day_buckets = {}
    for e in events:
        ts = e.get("created_at", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hour_buckets[dt.hour] = hour_buckets.get(dt.hour, 0) + 1
                day_name = dt.strftime("%A")
                day_buckets[day_name] = day_buckets.get(day_name, 0) + 1
            except ValueError:
                pass

    sorted_hours = sorted(hour_buckets.items(), key=lambda x: -x[1])
    peak_hours = [f"{h}:00 UTC ({c} events)" for h, c in sorted_hours[:3]] if sorted_hours else ["No data"]

    sorted_days = sorted(day_buckets.items(), key=lambda x: -x[1])
    active_days = [f"{d} ({c})" for d, c in sorted_days[:3]] if sorted_days else ["No data"]

    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    lang_str = ", ".join(f"{l} ({c})" for l, c in sorted(langs.items(), key=lambda x: -x[1])[:6])

    recent = []
    for e in events[:10]:
        etype = e.get("type", "Unknown").replace("Event", "")
        repo = e.get("repo", {}).get("name", "?")
        ts = e.get("created_at", "")[:10]
        recent.append(f"  [{ts}] {etype} on {repo}")

    event_types = {}
    for e in events:
        t = e.get("type", "Unknown")
        event_types[t] = event_types.get(t, 0) + 1
    type_str = ", ".join(f"{t}: {c}" for t, c in sorted(event_types.items(), key=lambda x: -x[1]))

    active_dates = {e.get("created_at", "")[:10] for e in events if e.get("created_at")}
    fork_count = sum(1 for r in repos if r.get("fork"))
    name = profile.get("name") or profile["login"]

    print(f"=== SURVEILLANCE REPORT: @{username} ===")
    print(f"Subject: {name} (@{profile['login']})")
    print(f"Followers: {profile.get('followers', 0)} | Following: {profile.get('following', 0)}")
    print(f"Public repos: {profile.get('public_repos', 0)} ({fork_count} forks)")
    print(f"Account age: since {profile.get('created_at', '')[:10]}")
    print(f"Company: {profile.get('company') or 'None'}")
    print(f"Bio: {profile.get('bio') or 'None'}")
    print()
    print("ACTIVITY PATTERNS:")
    print(f"  Peak hours (UTC): {', '.join(peak_hours)}")
    print(f"  Most active days: {', '.join(active_days)}")
    print(f"  Active dates (recent): {len(active_dates)} unique days")
    print(f"  Event breakdown: {type_str or 'None'}")
    print()
    print(f"LANGUAGES: {lang_str or 'None'}")
    print()
    print("RECENT ACTIVITY:")
    print("\n".join(recent) if recent else "  No recent activity found")
    print()
    print("=== DELIVER YOUR SURVEILLANCE REPORT ===")


if __name__ == "__main__":
    main()
