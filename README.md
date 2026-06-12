# World Cup 2026 — Clipping Schedule + Reminders

Two things live here:

1. **`index.html`** — a self-contained schedule page (open in any browser, or print to PDF via Cmd+P after clicking **All**).
2. **A Telegram reminder bot** — posts the day's clipping assignments to one shared group, twice: an evening-before heads-up (~6 PM ET) and a morning-of reminder (~8 AM ET). Runs free on GitHub Actions — no server, no laptop left on.

All match data lives in **`schedule.json`** (one file, used by both the page and the bot).

---

## One-time setup (≈5 min)

### 1. Create the bot
- In Telegram, message **@BotFather** → send `/newbot` → follow prompts.
- Copy the **bot token** it gives you (looks like `123456789:AAE...`).

### 2. Add the bot to your clippers' group
- Open the group → add the bot as a member.
- Send any message in the group, e.g. `/start@YourBotName`.

### 3. Get the group chat id
```bash
TELEGRAM_BOT_TOKEN=<your-token> python3 get_chat_id.py
```
Copy the **negative number** next to your group name — that's your `TELEGRAM_CHAT_ID`.
(If nothing shows up: in @BotFather, `/setprivacy` → your bot → **Disable**, post in the group again, re-run.)

### 4. Add both as GitHub repo secrets
In the repo: **Settings → Secrets and variables → Actions → New repository secret**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

That's it. The schedule in `.github/workflows/clip-reminders.yml` fires the reminders automatically.

---

## Test it
```bash
# Print what tomorrow's message would look like (no send):
python3 notify.py --date 2026-06-14 --mode tomorrow --dry-run

# Actually send (needs the two env vars set):
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python3 notify.py --date 2026-06-14 --mode today
```
You can also trigger a real run anytime from the repo's **Actions → Clip Reminders → Run workflow**.

---

## Updating the schedule (e.g. knockout matchups)
Edit **`schedule.json`** — add an entry per match:
```json
{
  "date": "2026-06-30",
  "time": "3:00 PM",
  "match": "Round of 32: TBD vs TBD",
  "covers": ["Spain"],
  "venue": "Stadium · City",
  "creators": ["PeakFighter"]
}
```
Commit and push. The bot and the page both pick it up — no code changes needed.

> Note: cron times are UTC and assume EDT (UTC-4), which holds for the whole tournament (Jun 11–Jul 19, 2026).
