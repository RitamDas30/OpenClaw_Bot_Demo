#!/usr/bin/env python3
"""Telegram push notifier for GitHub Spy daemon (stdlib-only)."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

STATE_DIR = Path.home() / ".openclaw" / "github-spy"
SUBSCRIBERS_FILE = STATE_DIR / "telegram_subscribers.json"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def get_bot_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        return token

    cfg = _load_json(OPENCLAW_CONFIG)
    return (
        cfg.get("channels", {})
        .get("telegram", {})
        .get("botToken", "")
        .strip()
    )


def list_subscribers() -> list[str]:
    data = _load_json(SUBSCRIBERS_FILE)
    subs = data.get("chat_ids", [])
    if not isinstance(subs, list):
        return []
    clean = []
    for sid in subs:
        sval = str(sid).strip()
        if sval and sval not in clean:
            clean.append(sval)
    return clean


def add_subscriber(chat_id: str) -> bool:
    chat_id = str(chat_id).strip()
    if not chat_id:
        return False
    subs = list_subscribers()
    if chat_id in subs:
        return False
    subs.append(chat_id)
    _save_json(SUBSCRIBERS_FILE, {"chat_ids": subs})
    return True


def remove_subscriber(chat_id: str) -> bool:
    chat_id = str(chat_id).strip()
    subs = list_subscribers()
    if chat_id not in subs:
        return False
    new_subs = [sid for sid in subs if sid != chat_id]
    _save_json(SUBSCRIBERS_FILE, {"chat_ids": new_subs})
    return True


def _split_message(text: str, max_len: int = 3500) -> list[str]:
    text = text.strip()
    if len(text) <= max_len:
        return [text]
    chunks = []
    buf = []
    size = 0
    for line in text.splitlines():
        line_len = len(line) + 1
        if size + line_len > max_len and buf:
            chunks.append("\n".join(buf))
            buf = [line]
            size = line_len
        else:
            buf.append(line)
            size += line_len
    if buf:
        chunks.append("\n".join(buf))
    return chunks


def send_to_chat(token: str, chat_id: str, text: str) -> bool:
    if not token:
        return False
    base_url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in _split_message(text):
        payload = urllib.parse.urlencode(
            {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": "true",
            }
        ).encode()
        req = urllib.request.Request(base_url, data=payload)
        try:
            with urllib.request.urlopen(req, timeout=12):
                pass
        except Exception:
            return False
    return True


def push_broadcast(text: str) -> tuple[int, int]:
    token = get_bot_token()
    subscribers = list_subscribers()
    success = 0
    failed = 0
    for chat_id in subscribers:
        if send_to_chat(token, chat_id, text):
            success += 1
        else:
            failed += 1
    return success, failed
