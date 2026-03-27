#!/usr/bin/env python3
"""Fetch GitHub activity data for surveillance report. Uses only stdlib."""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

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
        print("ERROR: No username provided. Usage: github_stalk.py <username>")
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
    events = api_get(f"/users/{username}/events/public?per_page=100") or []

    # Active hours analysis
    hour_buckets = {}
    day_buckets = {}
    for e in events:
        ts = e.get("created_at", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                h = dt.hour
                hour_buckets[h] = hour_buckets.get(h, 0) + 1
                day_name = dt.strftime("%A")
                day_buckets[day_name] = day_buckets.get(day_name, 0) + 1
            except ValueError:
                pass

    # Peak hours
    sorted_hours = sorted(hour_buckets.items(), key=lambda x: -x[1])
    peak_hours = [f"{h}:00 UTC ({c} events)" for h, c in sorted_hours[:3]] if sorted_hours else ["No data"]

    # Active days
    sorted_days = sorted(day_buckets.items(), key=lambda x: -x[1])
    active_days = [f"{d} ({c})" for d, c in sorted_days[:3]] if sorted_days else ["No data"]

    # Language breakdown
    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    lang_str = ", ".join(f"{l} ({c})" for l, c in sorted(langs.items(), key=lambda x: -x[1])[:6])

    # Recent activity
    recent = []
    for e in events[:10]:
        etype = e.get("type", "Unknown").replace("Event", "")
        repo = e.get("repo", {}).get("name", "?")
        ts = e.get("created_at", "")[:10]
        recent.append(f"  [{ts}] {etype} on {repo}")

    # Event type breakdown
    event_types = {}
    for e in events:
        t = e.get("type", "Unknown")
        event_types[t] = event_types.get(t, 0) + 1
    type_str = ", ".join(f"{t}: {c}" for t, c in sorted(event_types.items(), key=lambda x: -x[1]))

    # Unique active days in recent events
    active_dates = set()
    for e in events:
        ts = e.get("created_at", "")[:10]
        if ts:
            active_dates.add(ts)

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
