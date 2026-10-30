# 303  •  kyomi

> *minimalist, borderless discord moderation & security engine.*

---

### ✦ architecture

```text
303-kyomi/
├── bot.py             # gateway intents, self-healing path handler & cog loader
├── main.py            # pterodactyl / container entrypoint wrapper
├── database.py        # async sqlite engine (data/moderation.db)
├── dashboard.py       # embedded live web panel & status monitor
├── ui_theme.py        # monochrome dark palette (#0c0c0e) & embed builders
└── cogs/
    ├── moderation.py  # disciplinary suite & channel locks
    ├── automod.py     # borderless filter hud & ghost-ping detector
    ├── antiraid.py    # join velocity tracker & panic lockdown
    ├── dossier.py     # standing evaluation & member inspection
    ├── tickets.py     # custom emoji panels, category modal & archive locking
    ├── snapshot.py    # server structure backup, drift diff & disaster recovery
    ├── bumping.py     # disboard 2h reminder & bump leaderboard
    ├── logging_cog.py # ansi message diffs & member audit feeds
    └── help_cog.py    # floating operator manual modal
```

---

### ◈ operator manual

#### moderation & security
```text
/warn <user> <reason>         log strike (auto-escalates to mute/ban at threshold)
/warnings <user>              view active strikes for a member
/delwarn <id>                 remove a specific warning strike
/clearwarns <user>            clear all warnings for a member
/timeout <user> <mins>        mute member via discord timeout API
/untimeout <user>             remove timeout restriction
/kick <user> [reason]         kick member from guild
/ban <user> [reason]          permanently ban member
/unban <id>                   revoke ban by user ID
/purge <1-100> [user]         bulk delete recent messages
/slowmode <seconds>           adjust channel rate-limit (0 to disable)
/lock [reason]                lock channel for @everyone
/unlock                       restore normal channel send permissions
```

#### automod & anti-raid
```text
/automod panel                floating hud switches (anti-spam, links, invites, scam guard)
/automod addword <word>       append phrase to blocked word filter
/automod removeword <word>    remove phrase from blocked word filter
/antiraid panel               join velocity presets & new account quarantine age
/antiraid lockdown            emergency 1-click server lockdown (pauses invites & locks channels)
```

#### member dossier & context actions
```text
/dossier <user>               inspect standing (trusted/clean/watched/flagged), dates & notes
apps -> inspect user          right-click profile dossier inspector
apps -> delete & warn         right-click message removal & immediate strike
```

#### custom tickets & transcripts
```text
/ticket panel                 interactive modal builder (supports bold text, spacing & emojis)
/ticket setup                 configure active category, transcript channel, staff & archive role
/ticket archive               read-only lock, transcript export & duplicate creation freeze
/ticket add <user>            grant member access to current ticket room
/ticket remove <user>         revoke member access from current ticket room
/ticket rename <name>         rename active ticket channel
```

#### server snapshots & disaster recovery
```text
/snapshot create [label]      capture full server layout (roles, channels & overwrites)
/snapshot diff [id]           compare live server with backup to detect missing items
/snapshot restore <id>        disaster recovery (recreates missing roles & channels with perms)
/snapshot export <id>         download cold-storage .json file for offline backups
/snapshot list                display all saved backup points
/snapshot delete <id>         remove obsolete snapshot record
```

#### telemetry & utility
```text
/bump setup <ch> [role]       bind channel & staff ping for 2-hour disboard reminders
/bump leaderboard             display top guild bumpers
/bump autopromo               schedule recurring automated announcement text
/config modlog <channel>      bind primary moderation action log feed
/config auditlog <channel>    bind message edit/delete diff log feed
/config thresholds            set strike counts required for auto-mute and auto-ban
/help                         open floating operator popup manual
```

---

### ✧ configuration

```env
DISCORD_TOKEN=your_bot_token_here
DASHBOARD_PASSWORD=your_access_password
PORT=14828
DATABASE_PATH=data/moderation.db
```

---

### ⊘ production hosting

* **runtime**: python 3.11 / 3.12 (pterodactyl container).
* **storage**: persistent sqlite database (`data/moderation.db`).
* **web dashboard**: accessible via assigned container port (`http://<ip>:<port>`).
