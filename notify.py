#!/usr/bin/env python3
"""Post the day's clipping assignments to a Telegram group.

Reads schedule.json (the same data behind index.html) and sends a message
listing the matches to clip for a target day.

Modes:
  --mode today      -> matches for today's date (ET)        [morning-of reminder]
  --mode tomorrow   -> matches for tomorrow's date (ET)     [evening-before heads-up]
  --date YYYY-MM-DD -> override the target date (for testing)
  --dry-run         -> print the message instead of sending

Sending requires two environment variables (set as GitHub secrets in CI):
  TELEGRAM_BOT_TOKEN  -> from @BotFather
  TELEGRAM_CHAT_ID    -> the group chat id (negative number; use get_chat_id.py)
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover - fallback if tzdata missing
    ET = None

HERE = os.path.dirname(os.path.abspath(__file__))


def load_schedule():
    with open(os.path.join(HERE, "schedule.json"), encoding="utf-8") as f:
        return json.load(f)


def et_today():
    now = datetime.now(ET) if ET else datetime.utcnow()
    return now.date()


def time_key(t):
    """Turn '6:00 PM' into minutes since midnight for sorting."""
    try:
        return datetime.strptime(t.strip(), "%I:%M %p").hour * 60 + \
               datetime.strptime(t.strip(), "%I:%M %p").minute
    except ValueError:
        return 0


def build_message(matches, target_date, mode):
    d = datetime.strptime(target_date, "%Y-%m-%d")
    human = f"{d.strftime('%a')}, {d.strftime('%b')} {d.day}"
    when = "tomorrow" if mode == "tomorrow" else "today"
    emoji = "🎬" if mode == "tomorrow" else "📋"
    lines = [f"{emoji} <b>Clipping {when} — {human}</b>", ""]
    for m in matches:
        creators = " / ".join(m["creators"])
        covers = ", ".join(m["covers"])
        lines.append(f"<b>{m['time']} ET</b> — {m['match']}")
        lines.append(f"   📍 {m['venue']}")
        lines.append(f"   👤 {creators} · covers {covers}")
        lines.append("")
    n = len(matches)
    lines.append(f"{n} match{'' if n == 1 else 'es'} to clip. 🍿")
    return "\n".join(lines).strip()


def send(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["today", "tomorrow"], default="today")
    ap.add_argument("--date", help="override target date YYYY-MM-DD (testing)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.date:
        target = args.date
    else:
        base = et_today()
        if args.mode == "tomorrow":
            base = base + timedelta(days=1)
        target = base.isoformat()

    schedule = load_schedule()
    matches = sorted(
        (m for m in schedule if m["date"] == target),
        key=lambda m: time_key(m["time"]),
    )

    if not matches:
        print(f"No matches on {target} — nothing to send.")
        return

    text = build_message(matches, target, args.mode)
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if args.dry_run or not token or not chat_id:
        print("--- DRY RUN (no message sent) ---\n")
        print(text)
        if not args.dry_run and (not token or not chat_id):
            print("\n[!] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — would have failed to send.")
            sys.exit(1)
        return

    resp = send(token, chat_id, text)
    if not resp.get("ok"):
        print("Telegram API error:", resp)
        sys.exit(1)
    print(f"Sent {len(matches)} match(es) for {target}.")


if __name__ == "__main__":
    main()
