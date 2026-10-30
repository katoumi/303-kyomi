# 303  •  kyomi

internal documentation and operator reference for **303 kyomi**.
for private use only.

---

## ✦ architecture

```text
303-kyomi/
├── bot.py              # entry point, gateway intents & cog loader
├── database.py         # async sqlite engine (data/moderation.db)
├── dashboard.py        # embedded web panel & /health endpoint (port 3030)
├── ui_theme.py         # monochrome dark palette & embed builders
├── cogs/
│   ├── moderation.py   # /kick, /ban, /timeout, /warn, /purge, /lock
│   ├── automod.py      # borderless hud, spam/link/word filter, ghost-ping & scam guard
│   ├── antiraid.py     # join-velocity shield, account age gate & panic lockdown
│   ├── dossier.py      # right-click user inspector, trust score & staff notes
│   ├── tickets.py      # private support channels & live-countdown transcripts
│   ├── bumping.py      # disboard 2h tracker, leaderboard & scheduled autopromo
│   ├── logging_cog.py  # ansi message edit/delete diffs & entry/exit logs
│   └── help_cog.py     # floating modal manual (/help)
├── Dockerfile          # container spec for 24/7 cloud deployment
└── render.yaml         # render deployment manifest
```

---

## ◈ command reference

### moderation
- `/warn <user> <reason>` — log a strike (auto-mutes or auto-bans at threshold)
- `/warnings <user>` — view active warnings for a member
- `/delwarn <id>`  ·  `/clearwarns <user>` — remove one or all warnings
- `/timeout <user> <minutes> [reason]`  ·  `/untimeout <user>` — mute or unmute
- `/kick <user> [reason]` — kick a member from the server
- `/ban <user> [reason] [delete_days]`  ·  `/unban <user_id>` — ban or unban
- `/purge <1-100> [user]` — bulk delete messages in the current channel
- `/slowmode <seconds>` — set channel slowmode (`0` to disable)
- `/lock [reason]`  ·  `/unlock` — lock or unlock the current channel for `@everyone`

### automod & anti-raid (borderless hud)
- `/automod panel` *(or `/automod status`)* — open floating switches & dropdowns (automod, anti-spam, invites, links, ghost-ping, scam-guard, blocked words)
- `/automod addword <word>`  ·  `/automod removeword <word>` — edit word filter
- `/antiraid panel` — open anti-raid switches, join-velocity presets, and account age gate
- `/antiraid lockdown` — toggle emergency server lockdown (locks public channels & pauses invites for 2h)

### dossier & context menus
- `/dossier <user>` — inspect trust bar (`0–100%`), account dates, warnings, mod logs, and staff notes
- `right-click user -> apps -> inspect user` — open dossier from any user profile
- `right-click message -> apps -> delete & warn` — delete message and log a warning in one click

### tickets & transcripts
- `/ticket setup <category> <log_channel> [support_role]` — configure ticket category and transcript archive channel
- `/ticket panel [title] [description]` — post the persistent ticket dropdown menu

### bumping & telemetry
- `/bump setup <channel> [ping_role]` — bind channel and role for 2-hour disboard reminders
- `/bump leaderboard` — view top server bumpers and cooldown progress bar
- `/bump autopromo [channel] [interval_minutes] [message]` — schedule recurring promo messages
- `/bump simulate` — test the bump reminder with a 60-second timer
- `/config modlog <channel>`  ·  `/config auditlog <channel>` — set log channels
- `/config thresholds <mute_warns> <ban_warns>` — set warning escalation counts
- `/help` — open the floating manual modal

---

## ✧ local operation

```powershell
# 1. create virtual environment & install dependencies
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 2. configure environment variables in .env
# DISCORD_TOKEN=...
# DASHBOARD_PASSWORD=...

# 3. run bot & local web panel (http://localhost:3030)
.\.venv\Scripts\python.exe bot.py
```

---

## ⊘ 24/7 deployment notes

1. deploy repository as a web service on **render** or **koyeb** using `Dockerfile`.
2. set environment variables:
   - `DISCORD_TOKEN`
   - `DASHBOARD_PASSWORD`
   - `PORT` (`3030`)
3. point an uptime monitor (e.g. uptimerobot) to `https://<your-domain>/health` on a 5-minute interval to keep the instance active 24/7.
