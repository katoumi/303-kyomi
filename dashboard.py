import os
from aiohttp import web
import discord
from database import Database

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>303 kyomi  •  control panel</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #070709;
      --surface: #0d0d11;
      --surface-hover: #131319;
      --border: #1c1c24;
      --border-light: #282834;
      --text: #e6e6ee;
      --muted: #727285;
      --accent: #9e2233;
      --accent-glow: rgba(158, 34, 51, 0.25);
      --font: 'Inter', -apple-system, sans-serif;
      --mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      background-image:
        radial-gradient(circle at 15% 10%, rgba(158, 34, 51, 0.06), transparent 35%),
        radial-gradient(circle at 85% 80%, rgba(255, 255, 255, 0.02), transparent 40%);
      color: var(--text);
      font-family: var(--font);
      min-height: 100vh;
      padding: 34px 22px 60px;
      letter-spacing: -0.01em;
    }

    .container { max-width: 1080px; margin: 0 auto; }

    /* Auth Overlay */
    #authOverlay {
      position: fixed;
      inset: 0;
      background: rgba(7, 7, 9, 0.96);
      backdrop-filter: blur(10px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .auth-box {
      background: var(--surface);
      border: 1px solid var(--border-light);
      border-radius: 14px;
      padding: 32px 28px;
      width: 100%;
      max-width: 360px;
      text-align: center;
      box-shadow: 0 20px 50px rgba(0,0,0,0.8);
    }

    .auth-box h2 {
      font-size: 16px;
      font-weight: 500;
      text-transform: lowercase;
      margin-bottom: 6px;
    }

    .auth-box p {
      font-family: var(--mono);
      font-size: 11.5px;
      color: var(--muted);
      margin-bottom: 20px;
    }

    .auth-box input {
      width: 100%;
      background: #07070a;
      border: 1px solid var(--border-light);
      color: var(--text);
      padding: 11px 14px;
      border-radius: 8px;
      font-family: var(--mono);
      font-size: 13px;
      outline: none;
      margin-bottom: 12px;
      text-align: center;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 22px;
      margin-bottom: 28px;
      border-bottom: 1px solid var(--border);
    }

    .brand { display: flex; align-items: center; gap: 14px; }
    .brand-mark {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: #111117;
      border: 1px solid var(--border-light);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--mono);
      font-size: 13px;
      color: var(--text);
    }

    .brand-text h1 { font-size: 17px; font-weight: 500; text-transform: lowercase; }
    .brand-text p { font-size: 11.5px; color: var(--muted); font-family: var(--mono); margin-top: 2px; }

    .header-controls { display: flex; align-items: center; gap: 12px; }
    select.guild-picker {
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--border-light);
      padding: 8px 14px;
      border-radius: 8px;
      font-family: var(--mono);
      font-size: 12px;
      outline: none;
      cursor: pointer;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 7px 12px;
      border-radius: 99px;
      background: #121218;
      border: 1px solid var(--border-light);
      font-family: var(--mono);
      font-size: 11px;
      color: var(--text);
    }

    .grid {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 22px;
    }

    @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 22px;
      margin-bottom: 22px;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
    }

    .card-title {
      font-size: 13.5px;
      font-weight: 500;
      text-transform: lowercase;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .card-title span.tag { font-family: var(--mono); font-size: 11px; color: var(--muted); }

    .switch-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 15px;
      background: rgba(255, 255, 255, 0.012);
      border: 1px solid var(--border);
      border-radius: 10px;
      margin-bottom: 9px;
      transition: border-color 0.15s, background 0.15s;
    }

    .switch-row:hover { border-color: var(--border-light); background: var(--surface-hover); }
    .switch-info h3 { font-size: 13px; font-weight: 500; text-transform: lowercase; }
    .switch-info p { font-size: 11.5px; color: var(--muted); margin-top: 2px; }

    .toggle { position: relative; width: 42px; height: 22px; flex-shrink: 0; }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; cursor: pointer; inset: 0;
      background-color: #171720; border: 1px solid var(--border-light);
      border-radius: 99px; transition: 0.2s;
    }
    .slider:before {
      position: absolute; content: ""; height: 14px; width: 14px;
      left: 3px; bottom: 3px; background-color: var(--muted);
      border-radius: 50%; transition: 0.2s;
    }
    .toggle input:checked + .slider {
      background-color: var(--accent); border-color: #bf3044;
      box-shadow: 0 0 12px var(--accent-glow);
    }
    .toggle input:checked + .slider:before { transform: translateX(20px); background-color: #fff; }

    .params-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-top: 14px;
    }

    .param-box {
      background: rgba(255, 255, 255, 0.012);
      border: 1px solid var(--border);
      border-radius: 9px;
      padding: 10px 12px;
    }

    .param-box label {
      display: block; font-size: 11px; color: var(--muted);
      font-family: var(--mono); margin-bottom: 6px; text-transform: lowercase;
    }

    .param-box input {
      width: 100%; background: #07070a; border: 1px solid var(--border-light);
      color: var(--text); padding: 7px 9px; border-radius: 6px;
      font-family: var(--mono); font-size: 12.5px; outline: none;
    }

    .word-input-bar { display: flex; gap: 8px; margin-bottom: 14px; }
    .word-input-bar input {
      flex: 1; background: #07070a; border: 1px solid var(--border-light);
      color: var(--text); padding: 9px 13px; border-radius: 8px;
      font-family: var(--mono); font-size: 12px; outline: none;
    }

    .btn {
      background: #16161f; color: var(--text); border: 1px solid var(--border-light);
      padding: 8px 15px; border-radius: 8px; font-family: var(--mono);
      font-size: 11.5px; cursor: pointer; transition: 0.15s; text-transform: lowercase;
    }
    .btn:hover { background: var(--accent); border-color: #bf3044; color: #fff; }

    .tags-wrap { display: flex; flex-wrap: wrap; gap: 7px; min-height: 36px; }
    .word-tag {
      display: inline-flex; align-items: center; gap: 7px;
      background: #13131b; border: 1px solid var(--border-light);
      padding: 5px 10px; border-radius: 6px; font-family: var(--mono); font-size: 11.5px;
    }
    .word-tag button {
      background: none; border: none; color: var(--muted); cursor: pointer; font-size: 13px;
    }
    .word-tag button:hover { color: #ff5c70; }

    .feed-list { display: flex; flex-direction: column; gap: 8px; max-height: 320px; overflow-y: auto; }
    .feed-item {
      padding: 10px 12px; background: rgba(255, 255, 255, 0.012);
      border: 1px solid var(--border); border-radius: 8px; font-size: 12px;
    }
    .feed-item .meta { font-family: var(--mono); font-size: 10.5px; color: var(--muted); margin-top: 3px; }

    .toast {
      position: fixed; bottom: 22px; right: 22px;
      background: #13131b; border: 1px solid var(--border-light);
      border-left: 3px solid var(--accent); color: var(--text);
      padding: 10px 16px; border-radius: 8px; font-family: var(--mono);
      font-size: 11.5px; opacity: 0; transform: translateY(8px);
      transition: 0.2s; pointer-events: none;
    }
    .toast.show { opacity: 1; transform: translateY(0); }
    .empty-note { font-family: var(--mono); font-size: 11.5px; color: var(--muted); font-style: italic; }
  </style>
</head>
<body>
  <div id="authOverlay">
    <div class="auth-box">
      <h2>✦ 303 kyomi</h2>
      <p>enter dashboard passkey</p>
      <input type="password" id="passkeyInput" placeholder="passkey..." onkeydown="if(event.key==='Enter') unlockDashboard()">
      <button class="btn" style="width:100%" onclick="unlockDashboard()">unlock</button>
    </div>
  </div>

  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-mark">303</div>
        <div class="brand-text">
          <h1>303 kyomi</h1>
          <p>✦ web dashboard  ·  live server sync</p>
        </div>
      </div>
      <div class="header-controls">
        <select id="guildSelect" class="guild-picker" onchange="loadGuildData()"></select>
        <div class="status-badge">
          <span>● online</span>
        </div>
      </div>
    </header>

    <div class="grid">
      <div>
        <div class="card">
          <div class="card-header">
            <div class="card-title">✦ automod & anti-raid switches <span class="tag">// live</span></div>
          </div>

          <div class="switch-row">
            <div class="switch-info">
              <h3>◈ master automod</h3>
              <p>enable or pause automated message filtering</p>
            </div>
            <label class="toggle">
              <input type="checkbox" id="automod_enabled" onchange="saveSetting('automod_enabled', this.checked ? 1 : 0)">
              <span class="slider"></span>
            </label>
          </div>

          <div class="switch-row">
            <div class="switch-info">
              <h3>◈ anti-spam flood guard</h3>
              <p>auto-delete rapid message bursts & mute for 5m</p>
            </div>
            <label class="toggle">
              <input type="checkbox" id="anti_spam_enabled" onchange="saveSetting('anti_spam_enabled', this.checked ? 1 : 0)">
              <span class="slider"></span>
            </label>
          </div>

          <div class="switch-row">
            <div class="switch-info">
              <h3>⊘ ghost-ping detector</h3>
              <p>expose deleted or edited user/role mentions in chat</p>
            </div>
            <label class="toggle">
              <input type="checkbox" id="ghostping_enabled" onchange="saveSetting('ghostping_enabled', this.checked ? 1 : 0)">
              <span class="slider"></span>
            </label>
          </div>

          <div class="switch-row">
            <div class="switch-info">
              <h3>⊘ cross-channel scam guard</h3>
              <p>purge & mute accounts pasting identical text across 3+ channels</p>
            </div>
            <label class="toggle">
              <input type="checkbox" id="scam_guard_enabled" onchange="saveSetting('scam_guard_enabled', this.checked ? 1 : 0)">
              <span class="slider"></span>
            </label>
          </div>

          <div class="switch-row">
            <div class="switch-info">
              <h3>◇ block server invites</h3>
              <p>intercept discord.gg invite links from non-staff</p>
            </div>
            <label class="toggle">
              <input type="checkbox" id="block_invites" onchange="saveSetting('block_invites', this.checked ? 1 : 0)">
              <span class="slider"></span>
            </label>
          </div>

          <div class="switch-row">
            <div class="switch-info">
              <h3>◇ lock all external links</h3>
              <p>block all http/https links from regular members</p>
            </div>
            <label class="toggle">
              <input type="checkbox" id="block_links" onchange="saveSetting('block_links', this.checked ? 1 : 0)">
              <span class="slider"></span>
            </label>
          </div>

          <div class="switch-row">
            <div class="switch-info">
              <h3>† anti-raid shield</h3>
              <p>auto-lockdown on mass join bursts & block new alt accounts</p>
            </div>
            <label class="toggle">
              <input type="checkbox" id="antiraid_enabled" onchange="saveSetting('antiraid_enabled', this.checked ? 1 : 0)">
              <span class="slider"></span>
            </label>
          </div>

          <div class="params-grid">
            <div class="param-box">
              <label>spam msgs</label>
              <input type="number" id="spam_threshold" min="2" max="30" onchange="saveSetting('spam_threshold', parseInt(this.value))">
            </div>
            <div class="param-box">
              <label>spam window (s)</label>
              <input type="number" id="spam_interval_sec" min="1" max="60" onchange="saveSetting('spam_interval_sec', parseInt(this.value))">
            </div>
            <div class="param-box">
              <label>max pings / msg</label>
              <input type="number" id="max_mentions" min="0" max="50" onchange="saveSetting('max_mentions', parseInt(this.value))">
            </div>
            <div class="param-box">
              <label>warns -> mute</label>
              <input type="number" id="warn_threshold_timeout" min="0" max="20" onchange="saveSetting('warn_threshold_timeout', parseInt(this.value))">
            </div>
            <div class="param-box">
              <label>warns -> ban</label>
              <input type="number" id="warn_threshold_ban" min="0" max="30" onchange="saveSetting('warn_threshold_ban', parseInt(this.value))">
            </div>
            <div class="param-box">
              <label>min account age (d)</label>
              <input type="number" id="antiraid_min_account_days" min="0" max="30" onchange="saveSetting('antiraid_min_account_days', parseInt(this.value))">
            </div>
          </div>
        </div>
      </div>

      <div>
        <div class="card">
          <div class="card-header">
            <div class="card-title">⊘ blocked words <span class="tag" id="wordCountTag">// 0 terms</span></div>
          </div>

          <div class="word-input-bar">
            <input type="text" id="newWordInput" placeholder="type a word to block..." onkeydown="if(event.key==='Enter') addWord()">
            <button class="btn" onclick="addWord()">＋ block</button>
          </div>

          <div id="wordsContainer" class="tags-wrap"></div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">✧ recent mod cases <span class="tag">// live feed</span></div>
            <button class="btn" onclick="loadGuildData()" style="padding: 5px 10px; font-size: 11px;">↻ refresh</button>
          </div>
          <div id="casesContainer" class="feed-list"></div>
        </div>
      </div>
    </div>
  </div>

  <div id="toast" class="toast">saved</div>

  <script>
    let currentGuildId = null;
    let passkey = localStorage.getItem('kyomi_passkey') || '';

    function headers() {
      return { 'Content-Type': 'application/json', 'X-Passkey': passkey };
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = `╰ ${msg}`;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2200);
    }

    async function unlockDashboard() {
      passkey = document.getElementById('passkeyInput').value.trim();
      localStorage.setItem('kyomi_passkey', passkey);
      await init();
    }

    async function init() {
      const res = await fetch('/api/guilds', { headers: headers() });
      if (res.status === 401) {
        document.getElementById('authOverlay').style.display = 'flex';
        return;
      }
      document.getElementById('authOverlay').style.display = 'none';
      const data = await res.json();
      const sel = document.getElementById('guildSelect');
      sel.innerHTML = '';
      data.guilds.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.id;
        opt.textContent = `${g.name.toLowerCase()} (${g.member_count})`;
        sel.appendChild(opt);
      });
      if (data.guilds.length > 0) {
        currentGuildId = data.guilds[0].id;
        await loadGuildData();
      }
    }

    async function loadGuildData() {
      const sel = document.getElementById('guildSelect');
      currentGuildId = sel.value;
      if (!currentGuildId) return;

      const res = await fetch(`/api/guild/${currentGuildId}`, { headers: headers() });
      if (res.status === 401) {
        document.getElementById('authOverlay').style.display = 'flex';
        return;
      }
      const data = await res.json();
      const s = data.settings;

      document.getElementById('automod_enabled').checked = !!s.automod_enabled;
      document.getElementById('anti_spam_enabled').checked = !!s.anti_spam_enabled;
      document.getElementById('ghostping_enabled').checked = !!(s.ghostping_enabled ?? 1);
      document.getElementById('scam_guard_enabled').checked = !!(s.scam_guard_enabled ?? 1);
      document.getElementById('block_invites').checked = !!s.block_invites;
      document.getElementById('block_links').checked = !!s.block_links;
      document.getElementById('antiraid_enabled').checked = !!(s.antiraid_enabled ?? 1);

      document.getElementById('spam_threshold').value = s.spam_threshold ?? 5;
      document.getElementById('spam_interval_sec').value = s.spam_interval_sec ?? 5;
      document.getElementById('max_mentions').value = s.max_mentions ?? 5;
      document.getElementById('warn_threshold_timeout').value = s.warn_threshold_timeout ?? 3;
      document.getElementById('warn_threshold_ban').value = s.warn_threshold_ban ?? 5;
      document.getElementById('antiraid_min_account_days').value = s.antiraid_min_account_days ?? 2;

      renderWords(data.words);
      renderCases(data.cases);
    }

    function renderWords(words) {
      const wrap = document.getElementById('wordsContainer');
      document.getElementById('wordCountTag').textContent = `// ${words.length} terms`;
      if (!words.length) {
        wrap.innerHTML = '<span class="empty-note">no words blocked yet.</span>';
        return;
      }
      wrap.innerHTML = '';
      words.forEach(w => {
        const tag = document.createElement('div');
        tag.className = 'word-tag';
        tag.innerHTML = `<span>${w}</span><button onclick="removeWord('${w.replace(/'/g, "\\'")}')">&times;</button>`;
        wrap.appendChild(tag);
      });
    }

    function renderCases(cases) {
      const wrap = document.getElementById('casesContainer');
      if (!cases.length) {
        wrap.innerHTML = '<span class="empty-note">no mod logs recorded yet.</span>';
        return;
      }
      wrap.innerHTML = '';
      cases.forEach(c => {
        const item = document.createElement('div');
        item.className = 'feed-item';
        item.innerHTML = `
          <div><strong>#${c.id} · ${c.action}</strong> — ${c.reason}</div>
          <div class="meta">user: ${c.target_id}  ·  ${c.created_at}</div>
        `;
        wrap.appendChild(item);
      });
    }

    async function saveSetting(column, value) {
      if (!currentGuildId) return;
      await fetch(`/api/guild/${currentGuildId}/setting`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ column, value })
      });
      showToast(`updated ${column.replace(/_/g, ' ')}`);
    }

    async function addWord() {
      const input = document.getElementById('newWordInput');
      const word = input.value.trim().toLowerCase();
      if (!word || !currentGuildId) return;
      input.value = '';
      await fetch(`/api/guild/${currentGuildId}/words`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ action: 'add', word })
      });
      showToast(`blocked "${word}"`);
      await loadGuildData();
    }

    async function removeWord(word) {
      if (!currentGuildId) return;
      await fetch(`/api/guild/${currentGuildId}/words`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ action: 'remove', word })
      });
      showToast(`unblocked "${word}"`);
      await loadGuildData();
    }

    init();
  </script>
</body>
</html>
"""


class WebDashboard:
    """Embedded aiohttp web dashboard + healthcheck server for 24/7 cloud hosting."""

    def __init__(self, bot: discord.Client, db: Database, port: int = 3030):
        self.bot = bot
        self.db = db
        self.port = int(os.getenv("PORT", os.getenv("SERVER_PORT", port)))
        self.password = os.getenv("DASHBOARD_PASSWORD", "").strip()
        self.runner: web.AppRunner | None = None

    def _authorized(self, request: web.Request) -> bool:
        if not self.password:
            return True
        return request.headers.get("X-Passkey", "") == self.password

    async def handle_index(self, request: web.Request) -> web.Response:
        return web.Response(text=DASHBOARD_HTML, content_type="text/html")

    async def handle_health(self, request: web.Request) -> web.Response:
        import bot as bot_module
        return web.json_response(
            {
                "status": "online",
                "bot": str(self.bot.user) if self.bot.user else "starting",
                "guilds": len(self.bot.guilds),
                "has_token": bool(os.getenv("DISCORD_TOKEN")),
                "token_len": len(os.getenv("DISCORD_TOKEN") or ""),
                "last_error": getattr(bot_module, "last_bot_error", "none"),
                "retries": getattr(bot_module, "retry_count", 0),
            }
        )

    async def handle_logs(self, request: web.Request) -> web.Response:
        import bot as bot_module
        log_file = "bot.log"
        content = ""
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()[-6000:]
            except Exception as e:
                content = str(e)
        return web.Response(text=content or "no logs yet", content_type="text/plain")
        import bot as bot_module
        return web.json_response(
            {
                "status": "online",
                "bot": str(self.bot.user) if self.bot.user else "starting",
                "guilds": len(self.bot.guilds),
                "has_token": bool(os.getenv("DISCORD_TOKEN")),
                "token_len": len(os.getenv("DISCORD_TOKEN") or ""),
                "last_error": getattr(bot_module, "last_bot_error", "none"),
                "retries": getattr(bot_module, "retry_count", 0),
            }
        )

    async def handle_guilds(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guilds = [
            {
                "id": str(g.id),
                "name": g.name,
                "member_count": g.member_count or 0,
            }
            for g in self.bot.guilds
        ]
        return web.json_response({"guilds": guilds})

    async def handle_guild_data(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        settings = await self.db.get_guild_settings(guild_id)
        words = await self.db.get_bad_words(guild_id)

        assert self.db.conn is not None
        async with self.db.conn.execute(
            "SELECT * FROM mod_cases WHERE guild_id = ? ORDER BY id DESC LIMIT 15",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            cases = [dict(r) for r in rows]

        return web.json_response(
            {
                "settings": settings,
                "words": words,
                "cases": cases,
            }
        )

    async def handle_update_setting(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        body = await request.json()
        column = body.get("column")
        value = body.get("value")
        await self.db.update_guild_setting(guild_id, column, value)
        return web.json_response({"ok": True})

    async def handle_words(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        body = await request.json()
        action = body.get("action")
        word = body.get("word", "").strip().lower()
        if action == "add" and word:
            await self.db.add_bad_word(guild_id, word)
        elif action == "remove" and word:
            await self.db.remove_bad_word(guild_id, word)
        return web.json_response({"ok": True})

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/", self.handle_index)
        app.router.add_get("/health", self.handle_health)
        app.router.add_get("/logs", self.handle_logs)
        app.router.add_get("/api/guilds", self.handle_guilds)
        app.router.add_get("/api/guild/{guild_id}", self.handle_guild_data)
        app.router.add_post(
            "/api/guild/{guild_id}/setting", self.handle_update_setting
        )
        app.router.add_post("/api/guild/{guild_id}/words", self.handle_words)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await site.start()

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()
