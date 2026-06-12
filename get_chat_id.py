#!/usr/bin/env python3
"""Print the Telegram chat ids the bot can see.

Usage:
  1. Create the bot via @BotFather and copy its token.
  2. Add the bot to your clippers' group.
  3. In the group, send any message (e.g. /start@YourBotName).
  4. Run:  TELEGRAM_BOT_TOKEN=123:abc python3 get_chat_id.py
  5. Copy the negative id next to your group name -> that's TELEGRAM_CHAT_ID.

If no chats show up, the bot's privacy mode may be hiding group messages.
Fix: message @BotFather -> /setprivacy -> pick the bot -> Disable, then post
in the group again and re-run.
"""
import json
import os
import sys
import urllib.request

token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    sys.exit("Set TELEGRAM_BOT_TOKEN first, e.g. TELEGRAM_BOT_TOKEN=123:abc python3 get_chat_id.py")

with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates") as r:
    data = json.load(r)

seen = {}
for u in data.get("result", []):
    msg = u.get("message") or u.get("channel_post") or u.get("my_chat_member", {}) or {}
    chat = msg.get("chat")
    if chat:
        label = chat.get("title") or chat.get("username") or chat.get("first_name") or "?"
        seen[chat["id"]] = f"{label} ({chat.get('type')})"

if not seen:
    print("No chats found. Add the bot to the group, send a message there, then re-run.")
    print("If still empty, disable the bot's privacy mode in @BotFather (/setprivacy).")
else:
    print("chat_id\tname")
    for cid, name in seen.items():
        print(f"{cid}\t{name}")
