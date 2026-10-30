# 🛡️ Discord Moderation & Automation Bot

A modular, asynchronous Discord moderation and server automation bot built with **`discord.py` v2** and **`aiosqlite`**.

## ✨ Features

### 1. Slash Commands (`cogs/moderation.py`)
- `/kick <member> [reason]` — Kick a member with hierarchy validation and DM notification.
- `/ban <member> [reason] [delete_days]` — Ban a member and purge up to 7 days of their messages.
- `/unban <user_id> [reason]` — Unban a user by their numeric Discord ID.
- `/timeout <member> <minutes> [reason]` — Temporarily mute a member using Discord's native timeout.
- `/untimeout <member> [reason]` — Remove an active timeout from a member.
- `/purge <amount> [member]` — Bulk delete up to 100 messages (optionally filtered by user).
- `/warn <member> <reason>` — Issue a persistent warning. Automatically times out or bans when warning thresholds are reached!
- `/warnings <member>` — View a member's warning history.
- `/delwarn <warning_id>` & `/clearwarns <member>` — Remove a single warning or clear all warnings for a member.
- `/slowmode <seconds>` — Set or disable channel slowmode.
- `/lock [reason]` & `/unlock` — Quickly lock or unlock the current text channel during raids.

### 2. Auto-Moderation (`cogs/automod.py`)
- **Anti-Spam Rate Limiter**: Automatically deletes messages and applies a 5-minute timeout when a user exceeds the message rate threshold (default: 5 messages within 5 seconds).
- **Bad Word Filter**: Blocks messages containing server-configured words (`/automod addword`, `/automod removeword`).
- **Invite & Link Blocker**: Blocks unauthorized Discord server invites (`discord.gg/...`) and optionally all HTTP/HTTPS links.
- **Mass-Mention Protection**: Automatically deletes messages and times out users who exceed the maximum mention limit in a single message.
- **Control Panel**: View and toggle rules anytime with `/automod status` and `/automod toggle`.

### 3. Audit & Mod Logging (`cogs/logging_cog.py`)
- **Moderation Case Logs (`/config modlog`)**: Logs every `/kick`, `/ban`, `/timeout`, `/warn`, `/purge`, and AutoMod intervention with sequential Case IDs.
- **Server Audit Logs (`/config auditlog`)**:
  - 🗑️ Deleted messages (including attachment filenames)
  - ✏️ Edited messages (Before & After diff + jump link)
  - 📥 Member joins (with **New Account Alert** if the account is `< 7` days old)
  - 📤 Member leaves (with their previous roles)
- **Escalation Thresholds (`/config thresholds`)**: Configure how many warnings trigger an automatic 1-hour timeout (default: `3`) or permanent ban (default: `5`).

### 4. Right-Click Member Dossier & Trust Score (`cogs/dossier.py`)
- **Context Menu (`Right-Click User -> Apps -> 📋 Inspect Member Dossier` or `/dossier <member>`)**:
  - Calculates a live **`0–100` Trust Score** based on account age, server tenure, roles, warnings, and moderation history.
  - Displays active warnings, recent mod cases, and confidential **Staff Notes**.
  - Includes interactive **1-Click Action Buttons**: `[⚠️ Quick Warn]`, `[⏳ Timeout 15m]`, `[📝 Add Staff Note]`, and `[🧹 Clear Warnings]`.
- **Context Menu (`Right-Click Message -> Apps -> 🚨 Quick Delete & Warn Author`)**:
  - Instantly deletes a rule-breaking message, logs its contents to the mod-log channel, and issues a formal warning to the author in a single click.

### 5. Interactive Dropdown Ticket System (`cogs/tickets.py`)
- `/ticket setup <category> <log_channel> [support_role]` — Set where private ticket channels are created and where transcripts are archived.
- `/ticket panel` — Posts a persistent dropdown menu (*General Support*, *Report a Member*, *Moderation Appeal*, *Partnership Inquiry*) that continues working even after bot restarts.
- **Persistent Claim & Transcript Controls**: Inside each ticket, staff can click **`[🙋‍♂️ Claim Ticket]`** or **`[🔒 Close & Save Transcript]`**, which compiles the full conversation into a downloadable `.md` transcript file and posts it to your archive channel.

### 6. Smart Bump Tracker, Leaderboard & Auto-Promo (`cogs/bumping.py`)
- **Auto-Detection for Disboard (`/bump`)**: Automatically detects when any member successfully bumps the server via Disboard, thanks them, increments their all-time bump counter, and schedules a persistent **2-hour reminder**.
- `/bump setup <channel> [ping_role]` — Set the bump channel and optional `@Bumpers` role to ping the exact moment the 2-hour cooldown expires.
- `/bump leaderboard` — Displays the server's top all-time bumpers and a live countdown to the next available bump.
- `/bump autopromo [channel] [interval_minutes] [message]` — Hands-free recurring scheduler that posts your server's custom promo/bump embed every `N` minutes.

---

## 🚀 Setup Instructions

### Step 1: Create Your Discord Bot Application
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Navigate to the **Bot** tab on the left sidebar:
   - Click **Reset Token** to generate your `DISCORD_TOKEN`.
   - Scroll down to **Privileged Gateway Intents** and enable:
     - ✅ **Server Members Intent**
     - ✅ **Message Content Intent**
3. Navigate to **OAuth2 -> URL Generator**:
   - Under **Scopes**, check `bot` and `applications.commands`.
   - Under **Bot Permissions**, check:
     - `Kick Members`, `Ban Members`, `Moderate Members` (Timeouts)
     - `Manage Channels`, `Manage Messages`, `Read Message History`
     - `Send Messages`, `Embed Links`, `View Channels`
   - Copy the generated URL at the bottom and open it in your browser to invite the bot to your server.

### Step 2: Configure Environment & Install Dependencies
```powershell
# 1. Navigate to the project folder
cd C:\Users\Mhiko\.gemini\antigravity\scratch\discord-mod-bot

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
.\.venv\Scripts\pip install -r requirements.txt

# 4. Create your .env file and paste your bot token
Copy-Item .env.example .env
```
Edit `.env` and replace `your_discord_bot_token_here` with your Discord Bot Token.

### Step 3: Run the Bot
```powershell
.\.venv\Scripts\python bot.py
```

### Step 4: Initial Server Configuration
Once your bot is online in your server, run these slash commands:
1. `/config modlog #your-mod-log-channel` — Set where mod cases and AutoMod actions are posted.
2. `/config auditlog #your-audit-log-channel` — Set where message edits/deletes and joins/leaves are posted.
3. `/automod status` — Inspect your Auto-Moderation settings.
4. `/automod addword <word>` — Add any custom words you want filtered.
