#!/usr/bin/env python3
"""Watch a GitHub user or repo for new activity. Uses only stdlib.

Usage:
  github_watch.py <target> --check     Check for new events (called by cron)
  github_watch.py <target> --init      Initialize watch (mark current events as seen)
  github_watch.py <target> --status    Show watch status

State is stored in ~/.openclaw/github-spy/<target>.json
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
STATE_DIR = Path.home() / ".openclaw" / "github-spy"


def api_get(path: str, etag: str | None = None) -> tuple[int, dict | list | None, str | None]:
    """Returns (status_code, data, new_etag)."""
    url = f"{GITHUB_API}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "OpenClaw-GitHubSpy/1.0")
    if TOKEN:
        req.add_header("Authorization", f"token {TOKEN}")
    if etag:
        req.add_header("If-None-Match", etag)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            new_etag = resp.headers.get("ETag")
            data = json.loads(resp.read().decode())
            return 200, data, new_etag
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return 304, None, etag
        if e.code == 404:
            return 404, None, None
        if e.code == 403:
            print("ERROR: GitHub API rate limit exceeded. Try again later or set GITHUB_TOKEN for 5000 req/hr.")
            return 403, None, None
        if e.code == 401:
            print("ERROR: GITHUB_TOKEN is invalid.")
            return 401, None, None
        return e.code, None, None
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot reach GitHub API. Check your internet connection. ({e.reason})")
        return 0, None, None
    except Exception as e:
        print(f"ERROR: Unexpected failure: {e}")
        return 0, None, None


def load_state(target: str) -> dict:
    state_file = STATE_DIR / f"{target.replace('/', '__')}.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"seen_ids": [], "etag": None}


def save_state(target: str, state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / f"{target.replace('/', '__')}.json"
    # Keep only last 500 seen IDs to prevent unbounded growth
    state["seen_ids"] = state["seen_ids"][-500:]
    state_file.write_text(json.dumps(state, indent=2))


def format_event(event: dict) -> str | None:
    etype = event.get("type", "")
    actor = event.get("actor", {}).get("login", "?")
    repo = event.get("repo", {}).get("name", "?")

    if etype == "PushEvent":
        commits = event.get("payload", {}).get("commits", [])
        branch = event.get("payload", {}).get("ref", "").replace("refs/heads/", "")
        lines = [f"PUSH by {actor} to {repo} ({branch}) - {len(commits)} commit(s):"]
        for c in commits[:3]:
            msg = c["message"].split("\n")[0][:80]
            lines.append(f"  {c['sha'][:7]} {msg}")
        if len(commits) > 3:
            lines.append(f"  ... and {len(commits) - 3} more")
        return "\n".join(lines)

    elif etype == "ReleaseEvent":
        release = event.get("payload", {}).get("release", {})
        tag = release.get("tag_name", "?")
        return f"NEW RELEASE on {repo}: {tag} by {actor}"

    elif etype == "IssuesEvent":
        action = event.get("payload", {}).get("action", "opened")
        issue = event.get("payload", {}).get("issue", {})
        title = issue.get("title", "")
        num = issue.get("number", "?")
        if action == "opened":
            return f"NEW ISSUE #{num} on {repo}: {title} (by {actor})"

    elif etype == "PullRequestEvent":
        action = event.get("payload", {}).get("action", "opened")
        pr = event.get("payload", {}).get("pull_request", {})
        title = pr.get("title", "")
        num = pr.get("number", "?")
        if action == "opened":
            return f"NEW PR #{num} on {repo}: {title} (by {actor})"

    elif etype == "WatchEvent":
        return f"{actor} starred {repo}"

    elif etype == "CreateEvent":
        ref_type = event.get("payload", {}).get("ref_type", "")
        ref = event.get("payload", {}).get("ref", "")
        if ref_type == "repository":
            return f"{actor} created new repo {repo}"
        elif ref:
            return f"{actor} created {ref_type} '{ref}' on {repo}"

    return None


def check_target(target: str):
    state = load_state(target)

    if "/" in target:
        owner, repo = target.split("/", 1)
        api_path = f"/repos/{owner}/{repo}/events?per_page=50"
    else:
        api_path = f"/users/{target}/events/public?per_page=50"

    status, events, new_etag = api_get(api_path, state.get("etag"))

    if status == 304:
        # No new activity
        return

    if status != 200 or not events:
        if status == 404:
            print(f"Target '{target}' not found on GitHub.")
        return

    state["etag"] = new_etag
    seen = set(state.get("seen_ids", []))
    new_alerts = []

    for event in reversed(events):  # oldest first
        eid = event.get("id")
        if not eid or eid in seen:
            continue
        seen.add(eid)
        formatted = format_event(event)
        if formatted:
            new_alerts.append(formatted)

    state["seen_ids"] = list(seen)
    save_state(target, state)

    if new_alerts:
        print(f"=== NEW ACTIVITY for {target} ===")
        for alert in new_alerts:
            print(alert)
            print()
    # If no new alerts, print nothing (silent when no news)


def init_target(target: str):
    """Mark all current events as seen."""
    if "/" in target:
        owner, repo = target.split("/", 1)
        api_path = f"/repos/{owner}/{repo}/events?per_page=50"
    else:
        api_path = f"/users/{target}/events/public?per_page=50"

    status, events, etag = api_get(api_path)
    if status != 200:
        print(f"Failed to fetch events for '{target}' (status {status})")
        sys.exit(1)

    seen_ids = [e["id"] for e in (events or []) if "id" in e]
    save_state(target, {"seen_ids": seen_ids, "etag": etag})
    print(f"Initialized watch for '{target}'. {len(seen_ids)} existing events marked as seen.")


def show_status(target: str):
    state = load_state(target)
    seen_count = len(state.get("seen_ids", []))
    has_etag = bool(state.get("etag"))
    print(f"Watch status for '{target}':")
    print(f"  Seen events: {seen_count}")
    print(f"  ETag cached: {'yes' if has_etag else 'no'}")


def main():
    if len(sys.argv) < 3:
        print("Usage: github_watch.py <target> --check|--init|--status")
        sys.exit(1)

    target = sys.argv[1].lower()
    action = sys.argv[2]

    if action == "--init":
        init_target(target)
    elif action == "--check":
        check_target(target)
    elif action == "--status":
        show_status(target)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)


if __name__ == "__main__":
    main()
