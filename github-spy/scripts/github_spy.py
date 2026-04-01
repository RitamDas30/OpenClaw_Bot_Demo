#!/usr/bin/env python3
"""Unified lightweight GitHub Spy command dispatcher.

Usage examples:
  python3 scripts/github_spy.py roast torvalds
  python3 scripts/github_spy.py spy torvalds
  python3 scripts/github_spy.py "roast torvalds"
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from datetime import datetime

from github_api import GitHubApiError, fetch_profile, fetch_profile_events, fetch_user_parallel, parse_username
from github_watch import check_target, init_target, list_watch_targets, parse_target
from telegram_notifier import (
    add_subscriber,
    add_target_subscriber,
    get_latest_telegram_chat_id,
    list_subscribers,
    remove_subscriber,
)


def _extract_username(text: str) -> str:
    url_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([^/?#\s]+)", text, re.IGNORECASE)
    if url_match:
        return parse_username(url_match.group(0))

    words = text.split()
    for index, word in enumerate(words):
        if word.lower() in {"roast", "spy", "stalk", "activity", "watch", "user", "username"} and index + 1 < len(words):
            return parse_username(words[index + 1])

    if words:
        return parse_username(words[-1])
    raise ValueError("No GitHub username provided.")


def _detect_mode(text: str) -> str:
    lowered = text.lower()
    if "roast" in lowered:
        return "roast"
    if any(word in lowered for word in ("summary", "summarize", "strength", "skills", "stack")):
        return "summary"
    if any(word in lowered for word in ("watch", "track", "monitor", "24x7", "24*7")):
        return "watch-add"
    if any(word in lowered for word in ("updates", "new activity", "check activity", "check watch")):
        return "watch-check"
    if any(word in lowered for word in ("watch list", "list watches", "tracked users")):
        return "watch-list"
    if any(word in lowered for word in ("unsubscribe", "remove chat")):
        return "notify-remove"
    if any(word in lowered for word in ("subscribe", "notify me", "register chat")):
        return "notify-add"
    if any(word in lowered for word in ("notify list", "subscribers")):
        return "notify-list"
    return "spy"


def _fmt_date(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return ts[:10] if ts else "unknown-date"
    return dt.strftime("%Y-%m-%d")


def _build_spy_report(username: str, profile: dict, events: list[dict]) -> str:
    push_count = 0
    pr_open_count = 0
    commit_messages = []
    touched_repos = Counter()

    lines = [f"GitHub Spy Report: @{username}"]
    lines.append(f"Profile: followers={profile.get('followers', 0)}, public_repos={profile.get('public_repos', 0)}")

    for event in events:
        etype = event.get("type", "")
        repo = event.get("repo", {}).get("name", "?")
        touched_repos[repo] += 1
        if etype == "PushEvent":
            push_count += 1
            for commit in event.get("payload", {}).get("commits", [])[:2]:
                msg = (commit.get("message") or "").strip().splitlines()[0]
                if msg:
                    commit_messages.append(msg[:90])
        elif etype == "PullRequestEvent" and event.get("payload", {}).get("action") == "opened":
            pr_open_count += 1

    lines.append(
        f"Recent public activity window: {len(events)} events, pushes={push_count}, opened_prs={pr_open_count}"
    )

    if touched_repos:
        top_repos = ", ".join(name for name, _ in touched_repos.most_common(3))
        lines.append(f"Most active repos: {top_repos}")

    lines.append("Latest notable events:")
    for event in events[:5]:
        etype = (event.get("type") or "Unknown").replace("Event", "")
        repo = event.get("repo", {}).get("name", "?")
        created = _fmt_date(event.get("created_at", ""))
        lines.append(f"- {created}: {etype} on {repo}")

    if commit_messages:
        lines.append("Latest commit signals:")
        for msg in commit_messages[:4]:
            lines.append(f"- {msg}")
    else:
        lines.append("Latest commit signals: no recent public commits found.")

    return "\n".join(lines)


def _build_roast(username: str, profile: dict, repos: list[dict], events: list[dict]) -> str:
    original = [repo for repo in repos if not repo.get("fork")]
    forked = [repo for repo in repos if repo.get("fork")]
    stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    pushes = sum(1 for event in events if event.get("type") == "PushEvent")
    prs_opened = sum(
        1
        for event in events
        if event.get("type") == "PullRequestEvent" and event.get("payload", {}).get("action") == "opened"
    )

    commit_messages: list[str] = []
    for event in events:
        if event.get("type") != "PushEvent":
            continue
        for commit in event.get("payload", {}).get("commits", []):
            msg = (commit.get("message") or "").strip().splitlines()[0]
            if msg:
                commit_messages.append(msg[:90])

    weak_commit_keywords = ("fix", "temp", "quick", "wip", "oops", "todo", "hack", "debug")
    weak_commits = [msg for msg in commit_messages if any(key in msg.lower() for key in weak_commit_keywords)]
    activity_days = {event.get("created_at", "")[:10] for event in events if event.get("created_at")}

    roast_lines = [f"Roast for @{username}"]
    roast_lines.append(f"github.com/{username}")

    if not repos:
        roast_lines.append("You built such a stealth profile that even your repositories are classified.")
    elif len(forked) > len(original):
        roast_lines.append("You fork more than you forge. Original ideas are still buffering.")
    else:
        roast_lines.append("You ship code, but your commit history reads like a cliffhanger with no finale.")

    if stars == 0:
        roast_lines.append("Zero stars. Your projects are playing hide-and-seek with the algorithm.")
    elif stars < 10:
        roast_lines.append(f"{stars} stars total. That's indie-dev energy, keep grinding.")
    else:
        roast_lines.append(f"{stars} stars. Enough signal to be dangerous, not enough to coast.")

    roast_lines.append(
        f"Recent activity check: pushes={pushes}, opened_prs={prs_opened}, followers={profile.get('followers', 0)}."
    )
    if weak_commits:
        roast_lines.append(f"Commit quality audit: {len(weak_commits)} suspicious commit messages in recent activity.")
    if len(activity_days) < 3:
        roast_lines.append("Contribution pattern: stealth mode detected. Calendar is quieter than your README promises.")
    roast_lines.append("Friendly fire only: roast complete.")
    return "\n".join(roast_lines)


def _build_summary(username: str, profile: dict, repos: list[dict], events: list[dict]) -> str:
    langs = Counter((repo.get("language") or "Unknown") for repo in repos if repo.get("language"))
    top_langs = [name for name, _ in langs.most_common(3)]
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    push_events = [event for event in events if event.get("type") == "PushEvent"]
    prs_opened = sum(
        1
        for event in events
        if event.get("type") == "PullRequestEvent" and event.get("payload", {}).get("action") == "opened"
    )
    active_days = len({event.get("created_at", "")[:10] for event in events if event.get("created_at")})

    strengths = []
    if top_langs:
        strengths.append(f"Primary stack: {', '.join(top_langs)}")
    if total_stars >= 100:
        strengths.append(f"Strong OSS signal: {total_stars} total stars")
    if len(push_events) >= 10:
        strengths.append(f"Active contributor: {len(push_events)} push events in recent public window")
    if prs_opened >= 3:
        strengths.append(f"Collaboration signal: opened {prs_opened} PRs recently")
    if active_days >= 8:
        strengths.append(f"Consistency signal: active on {active_days} distinct recent days")

    if not strengths:
        strengths.append("Early-stage public profile; limited activity data to infer strengths confidently.")

    lines = [f"Summary for @{username}"]
    lines.append(f"Name: {profile.get('name') or profile.get('login')}")
    lines.append(f"Followers: {profile.get('followers', 0)} | Public repos: {profile.get('public_repos', 0)}")
    lines.append("Strength signals:")
    lines.extend(f"- {item}" for item in strengths)
    return "\n".join(lines)


def _watch_add(username_or_target: str) -> str:
    target = parse_target(username_or_target)
    init_target(target)
    lines = [f"Watch added: {target}"]

    auto_chat_id = get_latest_telegram_chat_id()
    if auto_chat_id and add_target_subscriber(target, auto_chat_id):
        lines.append(f"Auto-linked Telegram chat: {auto_chat_id}")
    elif auto_chat_id:
        lines.append(f"Telegram chat already linked: {auto_chat_id}")
    else:
        lines.append("Could not auto-detect Telegram chat id. Use: subscribe <chat_id>")

    lines.extend(
        [
            "24x7 mode is supported via daemon:",
            "python3 scripts/github_watch_daemon.py --interval 120",
        ]
    )
    return "\n".join(lines)


def _watch_check() -> str:
    targets = list_watch_targets()
    if not targets:
        return "No active watches. Add one with: watch <github_username_or_repo>"

    all_lines = []
    total_alerts = 0
    for target in targets:
        alerts = check_target(target, emit_output=False)
        if not alerts:
            continue
        total_alerts += len(alerts)
        all_lines.append(f"=== NEW ACTIVITY for {target} ===")
        all_lines.extend(alerts)
        all_lines.append("")

    if total_alerts == 0:
        return f"No new activity across {len(targets)} watched target(s)."
    return "\n".join(all_lines).strip()


def _watch_list() -> str:
    targets = list_watch_targets()
    if not targets:
        return "No active watches."
    lines = ["Watched targets:"]
    lines.extend(f"- {target}" for target in targets)
    return "\n".join(lines)


def _parse_chat_id(raw: str) -> str | None:
    match = re.search(r"-?\d{6,}", raw)
    if not match:
        return None
    return match.group(0)


def _notify_add(raw: str) -> str:
    chat_id = _parse_chat_id(raw)
    if not chat_id:
        return "ERROR: Missing chat id. Use: subscribe <chat_id> (from @userinfobot)."
    created = add_subscriber(chat_id)
    if created:
        return f"Telegram subscriber added: {chat_id}"
    return f"Telegram subscriber already exists: {chat_id}"


def _notify_remove(raw: str) -> str:
    chat_id = _parse_chat_id(raw)
    if not chat_id:
        return "ERROR: Missing chat id. Use: unsubscribe <chat_id>"
    removed = remove_subscriber(chat_id)
    if removed:
        return f"Telegram subscriber removed: {chat_id}"
    return f"No such Telegram subscriber: {chat_id}"


def _notify_list() -> str:
    subs = list_subscribers()
    if not subs:
        return "No Telegram subscribers registered."
    lines = ["Telegram subscribers:"]
    lines.extend(f"- {sid}" for sid in subs)
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print("ERROR: Missing input. Use: github_spy.py <mode username> or github_spy.py '<message>'")
        sys.exit(1)

    raw = " ".join(sys.argv[1:]).strip()
    words = raw.split()
    if len(words) >= 2 and words[0].lower() in {"roast", "spy", "summary", "watch-add", "notify-add", "notify-remove"}:
        mode = words[0].lower()
        username_input = " ".join(words[1:])
    elif len(words) >= 1 and words[0].lower() in {"watch-check", "watch-list", "notify-list"}:
        mode = words[0].lower()
        username_input = ""
    else:
        mode = _detect_mode(raw)
        username_input = raw

    if mode == "watch-list":
        print(_watch_list())
        return
    if mode == "watch-check":
        print(_watch_check())
        return
    if mode == "notify-list":
        print(_notify_list())
        return
    if mode == "notify-add":
        print(_notify_add(raw))
        return
    if mode == "notify-remove":
        print(_notify_remove(raw))
        return

    try:
        username = _extract_username(username_input)
    except ValueError as exc:
        print(f"ERROR: {exc} Please send a valid GitHub username (example: torvalds).")
        sys.exit(1)

    if mode == "watch-add":
        try:
            profile = fetch_profile(username)
        except GitHubApiError as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
        if not profile:
            print(f"ERROR: GitHub user '{username}' not found. Please send the correct username.")
            sys.exit(1)
        print(_watch_add(username))
        return

    if mode == "spy":
        try:
            profile, events = fetch_profile_events(username)
        except GitHubApiError as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
        if not profile:
            print(f"ERROR: GitHub user '{username}' not found. Please send the correct username.")
            sys.exit(1)
        print(_build_spy_report(username, profile, events))
        return

    try:
        profile, repos, events = fetch_user_parallel(username)
    except GitHubApiError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    if not profile:
        print(f"ERROR: GitHub user '{username}' not found. Please send the correct username.")
        sys.exit(1)

    if mode == "roast":
        print(_build_roast(username, profile, repos, events))
        return
    if mode == "summary":
        print(_build_summary(username, profile, repos, events))
        return

    print(_build_spy_report(username, profile, events))


if __name__ == "__main__":
    main()
