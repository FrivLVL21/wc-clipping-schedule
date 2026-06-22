#!/usr/bin/env python3
"""Poll Telegram for slash-commands and reply, in short bursts.

Runs on a GitHub Actions cron (~every 5 min). Each run long-polls getUpdates
for a few minutes, answers any commands, then exits. Cross-run de-duplication
is handled by Telegram's own offset confirmation, so no state file is needed.

Commands: /today  /tomorrow  /week  /schedule  /help
Replies go back to whatever chat the command came from (group or DM).

Lag note: this is "near real-time" only while a run is alive. Between runs
(and GitHub's scheduling delays) a command may wait a few minutes — Telegram
holds the update and the next run answers it.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    ET = None

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "210"))  # < 5-min cadence


def api(method, **params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{API}/{method}", data=data)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def load():
    with open(os.path.join(HERE, "schedule.json"), encoding="utf-8") as f:
        return json.load(f)


def tkey(t):
    return datetime.strptime(t.strip(), "%I:%M %p")


def et_today():
    return (datetime.now(ET) if ET else datetime.utcnow()).date()


def day_label(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.strftime('%a')}, {d.strftime('%b')} {d.day}"


def matches_on(sched, iso):
    return sorted((m for m in sched if m["date"] == iso), key=lambda m: tkey(m["time"]))


def fmt_day(matches, iso):
    if not matches:
        return f"📋 <b>{day_label(iso)}</b>\n\nNothing to clip — rest day. 🟢"
    body = "\n\n".join(
        f"<b>{m['time']} ET</b> — {m['match']}\n   👤 {' / '.join(m['creators'])}"
        for m in matches
    )
    return f"📋 <b>{day_label(iso)}</b>\n\n{body}\n\n{len(matches)} to clip. 🍿"


def fmt_range(sched, start, end, title):
    days = {}
    for m in sched:
        if start <= m["date"] <= end:
            days.setdefault(m["date"], []).append(m)
    if not days:
        return f"🗓 <b>{title}</b>\n\nNothing scheduled in this range."
    out = [f"🗓 <b>{title}</b>"]
    for iso in sorted(days):
        out.append(f"\n<b>{day_label(iso)}</b>")
        for m in sorted(days[iso], key=lambda m: tkey(m["time"])):
            out.append(f"  {m['time']} ET — {m['match']} · {' / '.join(m['creators'])}")
    n = sum(len(v) for v in days.values())
    out.append(f"\n{n} matches.")
    return "\n".join(out)


def handle(text, sched):
    cmd = text.strip().split()[0].lstrip("/").split("@")[0].lower()
    today = et_today()
    if cmd == "today":
        return fmt_day(matches_on(sched, today.isoformat()), today.isoformat())
    if cmd == "tomorrow":
        d = (today + timedelta(days=1)).isoformat()
        return fmt_day(matches_on(sched, d), d)
    if cmd == "week":
        end = today + timedelta(days=6)
        return fmt_range(sched, today.isoformat(), end.isoformat(),
                         f"Next 7 days ({day_label(today.isoformat())} – {day_label(end.isoformat())})")
    if cmd in ("schedule", "weekly"):
        s = min(m["date"] for m in sched)
        e = max(m["date"] for m in sched)
        return fmt_range(sched, s, e, "Full clipping schedule")
    if cmd in ("start", "help"):
        return ("👋 <b>WC Clipping Bot</b>\n\nCommands:\n"
                "/today — today's matches\n"
                "/tomorrow — tomorrow's matches\n"
                "/week — the next 7 days\n"
                "/weekly — the full weekly schedule\n"
                "/schedule — the whole schedule")
    return None


def main():
    if not TOKEN:
        sys.exit("TELEGRAM_BOT_TOKEN not set")
    sched = load()
    deadline = time.time() + RUN_SECONDS
    offset = None
    while time.time() < deadline:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset
            resp = api("getUpdates", **params)
        except Exception:
            time.sleep(3)
            continue
        for u in resp.get("result", []):
            offset = u["update_id"] + 1
            msg = u.get("message") or u.get("edited_message")
            if not msg:
                continue
            text = msg.get("text", "")
            if not text.startswith("/"):
                continue
            reply = handle(text, sched)
            if reply:
                try:
                    api("sendMessage", chat_id=msg["chat"]["id"], text=reply,
                        parse_mode="HTML", disable_web_page_preview="true")
                except Exception:
                    pass
    # Confirm everything we processed so the next run starts clean.
    if offset is not None:
        try:
            api("getUpdates", offset=offset, timeout=1)
        except Exception:
            pass


if __name__ == "__main__":
    main()
