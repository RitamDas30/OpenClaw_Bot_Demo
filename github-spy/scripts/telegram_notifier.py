#!/usr/bin/env python3
"""Telegram push notifier for GitHub Spy daemon (stdlib-only)."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

STATE_DIR = Path.home() / ".openclaw" / "github-spy"
SUBSCRIBERS_FILE = STATE_DIR / "telegram_subscribers.json"
TARGET_SUBSCRIBERS_FILE = STATE_DIR / "target_subscribers.json"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
SESSIONS_FILE = Path.home() / ".openclaw" / "agents" / "main" / "sessions" / "sessions.json"


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


def get_latest_telegram_chat_id(max_age_seconds: int = 900) -> str | None:
    """Best-effort chat-id discovery from OpenClaw session metadata.

    This enables fully automatic setup when user sends "watch <target>" from Telegram.
    """
    data = _load_json(SESSIONS_FILE)
    if not isinstance(data, dict):
        return None

    now_ms = int(time.time() * 1000)
    newest_ts = -1
    newest_chat: str | None = None
    fallback_ts = -1
    fallback_chat: str | None = None

    for _, session in data.items():
        if not isinstance(session, dict):
            continue
        origin = session.get("origin", {})
        if not isinstance(origin, dict):
            continue
        if origin.get("provider") != "telegram":
            continue
        updated_at = int(session.get("updatedAt") or 0)
        if updated_at <= 0:
            continue
        to_value = str(origin.get("to") or session.get("lastTo") or "").strip()
        if not to_value.startswith("telegram:"):
            continue
        chat_id = to_value.split("telegram:", 1)[1].strip()
        if not chat_id:
            continue
        if updated_at > fallback_ts:
            fallback_ts = updated_at
            fallback_chat = chat_id
        if now_ms - updated_at > max_age_seconds * 1000:
            continue
        if updated_at > newest_ts:
            newest_ts = updated_at
            newest_chat = chat_id
    return newest_chat or fallback_chat


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


def _load_target_subscribers() -> dict[str, list[str]]:
    data = _load_json(TARGET_SUBSCRIBERS_FILE)
    targets = data.get("targets", {})
    if not isinstance(targets, dict):
        return {}
    clean: dict[str, list[str]] = {}
    for target, chat_ids in targets.items():
        if not isinstance(chat_ids, list):
            continue
        tid = str(target).strip().lower()
        if not tid:
            continue
        deduped = []
        for cid in chat_ids:
            sid = str(cid).strip()
            if sid and sid not in deduped:
                deduped.append(sid)
        clean[tid] = deduped
    return clean


def _save_target_subscribers(targets: dict[str, list[str]]) -> None:
    _save_json(TARGET_SUBSCRIBERS_FILE, {"targets": targets})


def add_target_subscriber(target: str, chat_id: str) -> bool:
    target = str(target).strip().lower()
    chat_id = str(chat_id).strip()
    if not target or not chat_id:
        return False
    targets = _load_target_subscribers()
    existing = targets.get(target, [])
    if chat_id in existing:
        return False
    existing.append(chat_id)
    targets[target] = existing
    _save_target_subscribers(targets)
    return True


def list_target_subscribers(target: str) -> list[str]:
    target = str(target).strip().lower()
    if not target:
        return []
    targets = _load_target_subscribers()
    return targets.get(target, [])


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


def push_to_target(target: str, text: str) -> tuple[int, int]:
    token = get_bot_token()
    target_subscribers = list_target_subscribers(target)
    fallback_subscribers = list_subscribers()
    recipients = []
    for cid in target_subscribers + fallback_subscribers:
        if cid not in recipients:
            recipients.append(cid)

    success = 0
    failed = 0
    for chat_id in recipients:
        if send_to_chat(token, chat_id, text):
            success += 1
        else:
            failed += 1
    return success, failed
