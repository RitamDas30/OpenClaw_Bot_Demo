#!/usr/bin/env python3
"""Run GitHub watch checks in a lightweight 24x7 loop.

Usage:
  python3 scripts/github_watch_daemon.py --interval 120
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from github_watch import check_target, get_rate_limit_wait_seconds, list_watch_targets
from github_api import TOKEN
from telegram_notifier import list_subscribers, push_to_target


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def run_loop(interval_seconds: int) -> int:
    print(f"[{_now_utc()}] GitHub Spy daemon started. interval={interval_seconds}s")
    print(f"[{_now_utc()}] Press Ctrl+C to stop.")
    subscribers = list_subscribers()
    if subscribers:
        print(f"[{_now_utc()}] Telegram fallback broadcast enabled for {len(subscribers)} subscriber(s).")
    else:
        print(f"[{_now_utc()}] Telegram broadcast subscribers: none.")
    print(f"[{_now_utc()}] Target-specific Telegram delivery uses auto-linked watch chat ids.")
    if not TOKEN:
        print(f"[{_now_utc()}] GitHub token not found. Running in low-rate mode.")
        print(f"[{_now_utc()}] To raise limits, set GITHUB_TOKEN or create ~/.openclaw/github-spy/github_token.txt")
    while True:
        targets = list_watch_targets()
        if not TOKEN and targets:
            minimum_safe_interval = max(60, len(targets) * 70)
        else:
            minimum_safe_interval = interval_seconds
        effective_interval = max(interval_seconds, minimum_safe_interval)

        wait_seconds = get_rate_limit_wait_seconds()
        if wait_seconds > 0:
            print(f"[{_now_utc()}] GitHub rate-limited. Cooling down for {wait_seconds}s.")
            time.sleep(wait_seconds)
            continue

        if not targets:
            print(f"[{_now_utc()}] No active watches. Sleeping.")
        else:
            auth_state = "authenticated" if TOKEN else "unauthenticated"
            print(
                f"[{_now_utc()}] Checking {len(targets)} watched target(s). "
                f"mode={auth_state}, interval={effective_interval}s"
            )
        for target in targets:
            alerts = check_target(target, emit_output=False)
            if alerts:
                header = f"=== 🚨 NEW ACTIVITY for {target} ({_now_utc()}) ==="
                print(f"\n{header}")
                for alert in alerts:
                    print(alert)
                    print()
                message = "\n".join([header, *alerts])
                sent, failed = push_to_target(target, message)
                if sent or failed:
                    print(f"[{_now_utc()}] Telegram push: sent={sent}, failed={failed}")
        wait_seconds = get_rate_limit_wait_seconds()
        if wait_seconds > 0:
            print(f"[{_now_utc()}] Entering cooldown for {wait_seconds}s due to GitHub rate limit.")
            time.sleep(wait_seconds)
            continue
        time.sleep(effective_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GitHub watch checks continuously.")
    parser.add_argument("--interval", type=int, default=120, help="Polling interval in seconds (default: 120)")
    args = parser.parse_args()

    if args.interval < 30:
        print("ERROR: --interval must be at least 30 seconds.")
        sys.exit(1)

    try:
        run_loop(args.interval)
    except KeyboardInterrupt:
        print(f"\n[{_now_utc()}] Daemon stopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
