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

from github_watch import check_target, list_watch_targets
from telegram_notifier import list_subscribers, push_broadcast


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def run_loop(interval_seconds: int) -> int:
    print(f"[{_now_utc()}] GitHub Spy daemon started. interval={interval_seconds}s")
    print(f"[{_now_utc()}] Press Ctrl+C to stop.")
    subscribers = list_subscribers()
    if subscribers:
        print(f"[{_now_utc()}] Telegram push enabled for {len(subscribers)} subscriber(s).")
    else:
        print(f"[{_now_utc()}] Telegram push disabled (no subscribers registered).")
        print(f"[{_now_utc()}] Register once from Telegram chat: subscribe <your_chat_id>")
    while True:
        targets = list_watch_targets()
        if not targets:
            print(f"[{_now_utc()}] No active watches. Sleeping.")
        else:
            print(f"[{_now_utc()}] Checking {len(targets)} watched target(s).")
        for target in targets:
            alerts = check_target(target, emit_output=False)
            if alerts:
                header = f"=== 🚨 NEW ACTIVITY for {target} ({_now_utc()}) ==="
                print(f"\n{header}")
                for alert in alerts:
                    print(alert)
                    print()
                message = "\n".join([header, *alerts])
                sent, failed = push_broadcast(message)
                if sent or failed:
                    print(f"[{_now_utc()}] Telegram push: sent={sent}, failed={failed}")
        time.sleep(interval_seconds)


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
