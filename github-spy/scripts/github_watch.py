#!/usr/bin/env python3
"""Watch a GitHub user or repo for new activity. Uses only stdlib.

Usage:
  github_watch.py <target> --check     Check for new events (called by cron)
  github_watch.py <target> --init      Initialize watch (mark current events as seen)
  github_watch.py <target> --status    Show watch status
  github_watch.py --list               List all active watches

State is stored in ~/.openclaw/github-spy/<target>.json
"""

import json
import sys
from pathlib import Path
from github_api import TOKEN

STATE_DIR = Path.home() / ".openclaw" / "github-spy"


def load_state(target: str) -> dict:
    state_file = STATE_DIR / f"{target.replace('/', '__')}.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except json.JSONDecodeError:
            return {"seen_ids": [], "etag": None}
    return {"seen_ids": [], "etag": None}


def save_state(target: str, state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / f"{target.replace('/', '__')}.json"
    state["seen_ids"] = state["seen_ids"][-500:]
    state_file.write_text(json.dumps(state, indent=2))


def api_get_with_etag(path: str, etag: str | None = None) -> tuple[int, dict | list | None, str | None]:
    import urllib.request
    import urllib.error
    import os

    url = f"https://api.github.com{path}"
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
            print("ERROR: GitHub API rate limit exceeded.")
            return 403, None, None
        return e.code, None, None
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot reach GitHub API. ({e.reason})")
        return 0, None, None
    except Exception as e:
        print(f"ERROR: {e}")
        return 0, None, None


def format_event(event: dict) -> str | None:
    etype = event.get("type", "")
    actor = event.get("actor", {}).get("login", "?")
    repo = event.get("repo", {}).get("name", "?")

    if etype == "PushEvent":
        commits = event.get("payload", {}).get("commits", [])
        branch = event.get("payload", {}).get("ref", "").replace("refs/heads/", "")
        lines = [f"🔥 PUSH by {actor} to {repo} ({branch}) - {len(commits)} commit(s):"]
        for c in commits[:3]:
            msg = c["message"].split("\n")[0][:80]
            lines.append(f"  {c['sha'][:7]} {msg}")
        if len(commits) > 3:
            lines.append(f"  ... and {len(commits) - 3} more")
        return "\n".join(lines)
    elif etype == "ReleaseEvent":
        tag = event.get("payload", {}).get("release", {}).get("tag_name", "?")
        return f"🚀 NEW RELEASE on {repo}: {tag} by {actor}"
    elif etype == "IssuesEvent":
        action = event.get("payload", {}).get("action", "opened")
        issue = event.get("payload", {}).get("issue", {})
        if action == "opened":
            return f"🐛 NEW ISSUE #{issue.get('number', '?')} on {repo}: {issue.get('title', '')} (by {actor})"
    elif etype == "PullRequestEvent":
        action = event.get("payload", {}).get("action", "opened")
        pr = event.get("payload", {}).get("pull_request", {})
        if action == "opened":
            return f"📝 NEW PR #{pr.get('number', '?')} on {repo}: {pr.get('title', '')} (by {actor})"
    elif etype == "WatchEvent":
        return f"⭐ {actor} starred {repo}"
    elif etype == "CreateEvent":
        ref_type = event.get("payload", {}).get("ref_type", "")
        ref = event.get("payload", {}).get("ref", "")
        if ref_type == "repository":
            return f"🆕 {actor} created new repo {repo}"
        elif ref:
            return f"🔀 {actor} created {ref_type} '{ref}' on {repo}"
    elif etype == "ForkEvent":
        forkee = event.get("payload", {}).get("forkee", {}).get("full_name", "?")
        return f"🍴 {actor} forked {repo} → {forkee}"
    elif etype == "DeleteEvent":
        ref_type = event.get("payload", {}).get("ref_type", "")
        ref = event.get("payload", {}).get("ref", "")
        return f"🗑️ {actor} deleted {ref_type} '{ref}' on {repo}"
    return None


def parse_target(raw: str) -> str:
    raw = raw.strip()
    for prefix in ["https://github.com/", "http://github.com/", "github.com/"]:
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix):]
            break
    raw = raw.rstrip("/")
    raw = raw.lstrip("@")
    # Keep owner/repo format for repo watching
    parts = raw.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}".lower()
    return parts[0].lower()


def list_watch_targets() -> list[str]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    targets = []
    for file in STATE_DIR.glob("*.json"):
        if file.parent != STATE_DIR:
            continue
        targets.append(file.stem.replace("__", "/"))
    return sorted(targets)


def check_target(target: str, emit_output: bool = True) -> list[str]:
    state = load_state(target)

    if "/" in target:
        api_path = f"/repos/{target}/events?per_page=50"
    else:
        api_path = f"/users/{target}/events/public?per_page=50"

    status, events, new_etag = api_get_with_etag(api_path, state.get("etag"))

    if status == 304:
        return []
    if status != 200 or not events:
        if emit_output and status == 404:
            print(f"ERROR: Target '{target}' not found on GitHub.")
        return []

    state["etag"] = new_etag
    seen = set(state.get("seen_ids", []))
    new_alerts = []

    for event in reversed(events):
        eid = event.get("id")
        if not eid or eid in seen:
            continue
        seen.add(eid)
        formatted = format_event(event)
        if formatted:
            new_alerts.append(formatted)

    state["seen_ids"] = list(seen)
    save_state(target, state)

    if emit_output and new_alerts:
        print(f"=== 🚨 NEW ACTIVITY for {target} ===")
        for alert in new_alerts:
            print(alert)
            print()
    return new_alerts


def init_target(target: str):
    if "/" in target:
        api_path = f"/repos/{target}/events?per_page=50"
    else:
        api_path = f"/users/{target}/events/public?per_page=50"

    status, events, etag = api_get_with_etag(api_path)
    if status == 404:
        print(f"ERROR: Target '{target}' not found on GitHub.")
        sys.exit(1)
    if status != 200:
        print(f"ERROR: Failed to fetch events for '{target}' (status {status})")
        sys.exit(1)

    seen_ids = [e["id"] for e in (events or []) if "id" in e]
    save_state(target, {"seen_ids": seen_ids, "etag": etag})
    print(f"✅ Now watching '{target}'. {len(seen_ids)} existing events marked as seen.")


def show_status(target: str):
    state = load_state(target)
    seen_count = len(state.get("seen_ids", []))
    has_etag = bool(state.get("etag"))
    print(f"Watch status for '{target}':")
    print(f"  Seen events: {seen_count}")
    print(f"  ETag cached: {'yes' if has_etag else 'no'}")


def list_watches():
    targets = list_watch_targets()
    if not targets:
        print("No active watches.")
        return
    print("Active watches:")
    for name in targets:
        w = STATE_DIR / f"{name.replace('/', '__')}.json"
        state = json.loads(w.read_text())
        seen = len(state.get("seen_ids", []))
        print(f"  - {name} ({seen} events tracked)")


def main():
    if len(sys.argv) < 2:
        print("Usage: github_watch.py <target> --check|--init|--status")
        print("       github_watch.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_watches()
        return

    if len(sys.argv) < 3:
        print("Usage: github_watch.py <target> --check|--init|--status")
        sys.exit(1)

    target = parse_target(sys.argv[1])
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
