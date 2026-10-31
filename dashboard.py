import asyncio
import datetime
import io
import json
import logging
import os
import time
import aiohttp
from aiohttp import web
import discord

logger = logging.getLogger("mod-bot")

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>303 KYOMI // OPERATOR CONSOLE</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #070709;
      --surface: #0e0e12;
      --surface-hover: #14141a;
      --card: #111116;
      --border: #1b1b22;
      --border-light: #262632;
      --text: #eaebee;
      --muted: #6f7082;
      --accent: #8a1c27;
      --accent-glow: rgba(138, 28, 39, 0.25);
      --mint: #5bb98c;
      --mint-glow: rgba(91, 185, 140, 0.2);
      --amber: #d4a359;
      --font: 'Inter', -apple-system, sans-serif;
      --mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      background-image:
        radial-gradient(circle at 10% 5%, rgba(138, 28, 39, 0.08), transparent 30%),
        radial-gradient(circle at 90% 85%, rgba(255, 255, 255, 0.02), transparent 40%);
      color: var(--text);
      font-family: var(--font);
      min-height: 100vh;
      padding: 24px 20px 60px;
      letter-spacing: -0.01em;
    }

    .container { max-width: 1140px; margin: 0 auto; }

    /* Auth Overlay */
    #authOverlay {
      position: fixed; inset: 0;
      background: rgba(7, 7, 9, 0.96); backdrop-filter: blur(12px);
      display: flex; align-items: center; justify-content: center; z-index: 9999;
    }
    .auth-box {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 32px; width: 100%; max-width: 380px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.8);
    }
    .auth-box h2 {
      font-size: 15px; font-weight: 600; text-transform: lowercase;
      letter-spacing: 0.05em; color: var(--text); margin-bottom: 8px; font-family: var(--mono);
    }
    .auth-box p { font-size: 12px; color: var(--muted); margin-bottom: 20px; }

    /* Header & Vitals */
    header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 20px; flex-wrap: wrap; gap: 16px;
    }
    .brand { display: flex; align-items: center; gap: 14px; }
    .brand-mark {
      width: 36px; height: 36px; background: var(--surface);
      border: 1px solid var(--border); border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
      font-family: var(--mono); font-size: 13px; font-weight: 700; color: #fff;
    }
    .brand-title { font-size: 15px; font-weight: 600; letter-spacing: -0.02em; }
    .brand-sub { font-size: 11px; color: var(--muted); font-family: var(--mono); }

    .header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .pill {
      font-family: var(--mono); font-size: 11px; padding: 6px 12px;
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 20px; display: inline-flex; align-items: center; gap: 6px;
      color: var(--muted);
    }
    .pill.online { color: var(--mint); border-color: rgba(91, 185, 140, 0.3); background: var(--mint-glow); }
    .pill-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

    select.guild-select {
      background: var(--surface); color: var(--text); border: 1px solid var(--border);
      border-radius: 8px; padding: 7px 12px; font-size: 12px; font-family: var(--mono);
      cursor: pointer; outline: none; transition: border-color 0.15s;
    }
    select.guild-select:focus { border-color: var(--border-light); }

    /* Vitals Bar */
    .vitals-bar {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px; margin-bottom: 22px;
    }
    .vital-card {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 10px; padding: 14px 16px;
    }
    .vital-label { font-size: 11px; color: var(--muted); font-family: var(--mono); margin-bottom: 4px; }
    .vital-val { font-size: 17px; font-weight: 600; font-family: var(--mono); color: #fff; }

    /* Tabs Navigation */
    .tabs-nav {
      display: flex; gap: 6px; border-bottom: 1px solid var(--border);
      padding-bottom: 12px; margin-bottom: 24px; overflow-x: auto;
    }
    .tab-btn {
      background: transparent; border: 1px solid transparent; color: var(--muted);
      font-family: var(--mono); font-size: 12px; padding: 8px 16px; border-radius: 8px;
      cursor: pointer; transition: all 0.15s; white-space: nowrap; display: flex; align-items: center; gap: 6px;
    }
    .tab-btn:hover { color: var(--text); background: var(--surface); }
    .tab-btn.active {
      color: #fff; background: var(--surface); border-color: var(--border-light);
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .tab-btn .badge {
      font-size: 10px; background: rgba(255,255,255,0.08); padding: 2px 6px;
      border-radius: 10px; color: var(--text);
    }

    /* Tab Panes */
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }

    /* Standard Cards & Layout */
    .grid-2 { display: grid; grid-template-columns: 1.4fr 1fr; gap: 18px; }
    @media (max-width: 860px) { .grid-2 { grid-template-columns: 1fr; } }

    .card {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 20px; margin-bottom: 18px;
    }
    .card-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border);
    }
    .card-title {
      font-size: 13px; font-weight: 600; font-family: var(--mono);
      text-transform: lowercase; color: var(--text); display: flex; align-items: center; gap: 8px;
    }

    /* Form Controls */
    .setting-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.03);
    }
    .setting-row:last-child { border-bottom: none; }
    .setting-info { max-width: 70%; }
    .setting-name { font-size: 13px; font-weight: 500; margin-bottom: 2px; }
    .setting-desc { font-size: 11px; color: var(--muted); }

    /* Switches */
    .switch { position: relative; display: inline-block; width: 38px; height: 20px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; cursor: pointer; inset: 0;
      background-color: #202028; border-radius: 20px; transition: 0.2s;
    }
    .slider:before {
      position: absolute; content: ""; height: 14px; width: 14px; left: 3px; bottom: 3px;
      background-color: #8c8d9e; border-radius: 50%; transition: 0.2s;
    }
    input:checked + .slider { background-color: var(--accent); }
    input:checked + .slider:before { transform: translateX(18px); background-color: #fff; }

    /* Inputs & Buttons */
    input[type="text"], input[type="password"], input[type="number"] {
      background: var(--card); border: 1px solid var(--border);
      color: var(--text); padding: 8px 12px; border-radius: 6px;
      font-size: 12px; font-family: var(--mono); outline: none; transition: border-color 0.15s;
    }
    input[type="text"]:focus, input[type="password"]:focus, input[type="number"]:focus {
      border-color: var(--border-light);
    }
    .btn {
      background: var(--card); border: 1px solid var(--border);
      color: var(--text); padding: 8px 14px; border-radius: 6px;
      font-size: 12px; font-family: var(--mono); cursor: pointer;
      display: inline-flex; align-items: center; gap: 6px; transition: all 0.15s;
    }
    .btn:hover { background: var(--surface-hover); border-color: var(--border-light); }
    .btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
    .btn.primary:hover { opacity: 0.9; }
    .btn.danger { background: rgba(138, 28, 39, 0.2); border-color: var(--accent); color: #ff8b97; }
    .btn.danger:hover { background: var(--accent); color: #fff; }

    /* Tables */
    table { width: 100%; border-collapse: collapse; font-size: 12px; font-family: var(--mono); }
    th { text-align: left; color: var(--muted); padding: 10px 12px; border-bottom: 1px solid var(--border); font-weight: 500; }
    td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.03); }
    tr:hover td { background: rgba(255,255,255,0.015); }

    /* Tags */
    .tag {
      font-size: 10px; padding: 2px 7px; border-radius: 4px;
      background: rgba(255,255,255,0.06); color: var(--muted); display: inline-block;
    }
    .tag.open { background: var(--mint-glow); color: var(--mint); }
    .tag.archived { background: rgba(212, 163, 89, 0.15); color: var(--amber); }
    .tag.closed { background: rgba(255,255,255,0.04); color: var(--muted); }

    /* Terminal logs */
    .terminal-box {
      background: #050507; border: 1px solid var(--border);
      border-radius: 8px; padding: 14px; font-family: var(--mono);
      font-size: 11px; line-height: 1.6; color: #b4b5c4; max-height: 340px;
      overflow-y: auto; white-space: pre-wrap; word-break: break-all;
    }

    /* Word Tags */
    .word-cloud { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
    .word-chip {
      background: var(--card); border: 1px solid var(--border);
      border-radius: 20px; padding: 3px 10px; font-size: 11px;
      display: inline-flex; align-items: center; gap: 6px; font-family: var(--mono);
    }
    .word-del { cursor: pointer; color: var(--muted); font-weight: bold; }
    .word-del:hover { color: #ff6b7b; }
  </style>
</head>
<body>
  <!-- Passkey Overlay -->
  <div id="authOverlay" style="display: none;">
    <div class="auth-box">
      <h2>✦ operator authentication</h2>
      <p>enter the dashboard passkey configured in .env</p>
      <input type="password" id="passkeyInput" placeholder="passkey..." style="width: 100%; margin-bottom: 14px;">
      <button class="btn primary" style="width: 100%; justify-content: center;" onclick="verifyPasskey()">unlock dashboard</button>
    </div>
  </div>

  <div class="container">
    <!-- Header -->
    <header>
      <div class="brand">
        <div class="brand-mark">303</div>
        <div>
          <div class="brand-title">303 kyomi // console</div>
          <div class="brand-sub">security, automation & recovery engine</div>
        </div>
      </div>
      <div class="header-actions">
        <div class="pill online"><div class="pill-dot"></div><span id="gatewayStatus">gateway connected</span></div>
        <select id="guildSelect" class="guild-select" onchange="loadGuildData()">
          <option value="">loading servers...</option>
        </select>
      </div>
    </header>

    <!-- Vitals Bar -->
    <div class="vitals-bar">
      <div class="vital-card">
        <div class="vital-label">gateway ping</div>
        <div class="vital-val" id="vitalPing">-- ms</div>
      </div>
      <div class="vital-card">
        <div class="vital-label">uptime</div>
        <div class="vital-val" id="vitalUptime">--</div>
      </div>
      <div class="vital-card">
        <div class="vital-label">members cached</div>
        <div class="vital-val" id="vitalMembers">--</div>
      </div>
      <div class="vital-card">
        <div class="vital-label">database size</div>
        <div class="vital-val" id="vitalDbSize">-- KB</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs-nav">
      <button class="tab-btn active" onclick="switchTab('automod')">✦ automod & security</button>
      <button class="tab-btn" onclick="switchTab('tickets')">◈ tickets <span class="badge" id="ticketCountBadge">0</span></button>
      <button class="tab-btn" onclick="switchTab('dossier')">✧ member dossier</button>
      <button class="tab-btn" onclick="switchTab('snapshots')">◇ snapshots & recovery</button>
      <button class="tab-btn" onclick="switchTab('bumping')">⊘ bump tracker</button>
      <button class="tab-btn" onclick="switchTab('system')">† system & logs</button>
    </div>

    <!-- TAB 1: AUTOMOD & SECURITY -->
    <div id="tab-automod" class="tab-pane active">
      <div class="grid-2">
        <div>
          <div class="card">
            <div class="card-header">
              <div class="card-title">✦ core automod switches</div>
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <div class="setting-name">master automod</div>
                <div class="setting-desc">globally enables or pauses all automated message filtration</div>
              </div>
              <label class="switch"><input type="checkbox" id="sw_automod" onchange="toggleSetting('automod_enabled', this.checked)"><span class="slider"></span></label>
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <div class="setting-name">anti-spam flood guard</div>
                <div class="setting-desc">auto-deletes rapid message bursts & mutes sender for 5m</div>
              </div>
              <label class="switch"><input type="checkbox" id="sw_antispam" onchange="toggleSetting('anti_spam_enabled', this.checked)"><span class="slider"></span></label>
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <div class="setting-name">ghost-ping detector</div>
                <div class="setting-desc">exposes deleted or edited user/role mentions immediately</div>
              </div>
              <label class="switch"><input type="checkbox" id="sw_ghostping" onchange="toggleSetting('ghostping_enabled', this.checked)"><span class="slider"></span></label>
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <div class="setting-name">cross-channel scam guard</div>
                <div class="setting-desc">auto-purges identical messages broadcasted across 3+ channels</div>
              </div>
              <label class="switch"><input type="checkbox" id="sw_scam" onchange="toggleSetting('scam_guard_enabled', this.checked)"><span class="slider"></span></label>
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <div class="setting-name">block server invites</div>
                <div class="setting-desc">intercepts discord.gg links from regular members</div>
              </div>
              <label class="switch"><input type="checkbox" id="sw_invites" onchange="toggleSetting('block_invites_enabled', this.checked)"><span class="slider"></span></label>
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <div class="setting-name">lock external links</div>
                <div class="setting-desc">blocks all external http/https URLs from non-staff</div>
              </div>
              <label class="switch"><input type="checkbox" id="sw_links" onchange="toggleSetting('block_links_enabled', this.checked)"><span class="slider"></span></label>
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <div class="setting-name">anti-raid shield</div>
                <div class="setting-desc">quarantines accounts younger than min days & monitors join velocity</div>
              </div>
              <label class="switch"><input type="checkbox" id="sw_antiraid" onchange="toggleSetting('antiraid_enabled', this.checked)"><span class="slider"></span></label>
            </div>
          </div>
        </div>

        <div>
          <!-- Word Filter -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">⊘ blocked word filter</div>
            </div>
            <div style="display: flex; gap: 8px;">
              <input type="text" id="newWordInput" placeholder="add word or phrase..." style="flex: 1;">
              <button class="btn" onclick="addWord()">+ block</button>
            </div>
            <div class="word-cloud" id="wordCloud"></div>
          </div>

          <!-- Mod Cases -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">◈ recent moderation strikes</div>
              <button class="btn" onclick="loadGuildData()" style="padding: 4px 8px; font-size: 11px;">refresh</button>
            </div>
            <div style="max-height: 280px; overflow-y: auto;">
              <table id="modCasesTable">
                <thead><tr><th>action</th><th>user</th><th>reason</th></tr></thead>
                <tbody><tr><td colspan="3" style="color: var(--muted);">loading cases...</td></tr></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: TICKETS & TRANSCRIPTS -->
    <div id="tab-tickets" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <div class="card-title">◈ live tickets & support records</div>
          <button class="btn" onclick="loadTickets()">refresh tickets</button>
        </div>
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>id</th>
                <th>category</th>
                <th>opener</th>
                <th>status</th>
                <th>created</th>
                <th>actions</th>
              </tr>
            </thead>
            <tbody id="ticketsTableBody">
              <tr><td colspan="6" style="color: var(--muted);">loading tickets...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 3: MEMBER DOSSIER -->
    <div id="tab-dossier" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <div class="card-title">✧ member dossier search</div>
        </div>
        <div style="display: flex; gap: 8px; margin-bottom: 20px;">
          <input type="text" id="dossierSearchInput" placeholder="enter user id or username..." style="flex: 1;">
          <button class="btn primary" onclick="lookupDossier()">search user</button>
        </div>

        <div id="dossierResult" style="display: none;">
          <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 18px; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
            <img id="dossierAvatar" style="width: 54px; height: 54px; border-radius: 50%; border: 1px solid var(--border);" src="">
            <div>
              <div style="font-size: 16px; font-weight: 600;" id="dossierName">kato</div>
              <div style="font-size: 11px; color: var(--muted); font-family: var(--mono);" id="dossierMeta">id: 0 · created: --</div>
            </div>
            <div style="margin-left: auto;">
              <div class="pill" id="dossierStanding">trusted</div>
            </div>
          </div>

          <div class="grid-2">
            <div>
              <div style="font-size: 12px; font-weight: 600; font-family: var(--mono); margin-bottom: 8px;">active strikes & history</div>
              <div id="dossierStrikes" style="font-size: 12px; color: var(--muted); font-family: var(--mono); line-height: 1.6;">no strikes recorded.</div>
            </div>
            <div>
              <div style="font-size: 12px; font-weight: 600; font-family: var(--mono); margin-bottom: 8px;">staff notes</div>
              <div id="dossierNotesList" style="margin-bottom: 12px; font-size: 12px; font-family: var(--mono);"></div>
              <div style="display: flex; gap: 6px;">
                <input type="text" id="newNoteInput" placeholder="write staff note..." style="flex: 1;">
                <button class="btn" onclick="addDossierNote()">+ add</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: SNAPSHOTS & RECOVERY -->
    <div id="tab-snapshots" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <div class="card-title">◇ server structure backups</div>
          <button class="btn primary" onclick="createWebSnapshot()">+ create snapshot</button>
        </div>
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>id</th>
                <th>label</th>
                <th>channels</th>
                <th>roles</th>
                <th>created</th>
                <th>actions</th>
              </tr>
            </thead>
            <tbody id="snapshotsTableBody">
              <tr><td colspan="6" style="color: var(--muted);">loading snapshots...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 5: BUMP TRACKER -->
    <div id="tab-bumping" class="tab-pane">
      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <div class="card-title">⊘ disboard 2h countdown</div>
          </div>
          <div style="text-align: center; padding: 24px 0;">
            <div style="font-size: 32px; font-weight: 700; font-family: var(--mono); margin-bottom: 8px;" id="bumpTimerVal">--:--:--</div>
            <div style="font-size: 12px; color: var(--muted); font-family: var(--mono);" id="bumpStatusDesc">calculating next bump slot...</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">◈ top bumpers leaderboard</div>
          </div>
          <table>
            <thead><tr><th>rank</th><th>member</th><th>bumps</th></tr></thead>
            <tbody id="bumpLeaderboardBody">
              <tr><td colspan="3" style="color: var(--muted);">loading leaderboard...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 6: SYSTEM & LOGS -->
    <div id="tab-system" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <div class="card-title">† live terminal log stream</div>
          <button class="btn" onclick="fetchLogs()">refresh logs</button>
        </div>
        <div class="terminal-box" id="terminalLogs">loading output stream...</div>
      </div>
    </div>

  </div>

  <script>
    let currentGuildId = "";
    let passkey = localStorage.getItem("kyomi_passkey") || "";

    function authHeaders() {
      return { "X-Passkey": passkey, "Content-Type": "application/json" };
    }

    function switchTab(tabId) {
      document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));
      document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
      const target = document.getElementById("tab-" + tabId);
      if (target) target.classList.add("active");
      event.currentTarget.classList.add("active");

      if (tabId === "tickets") loadTickets();
      if (tabId === "snapshots") loadSnapshots();
      if (tabId === "bumping") loadBumpData();
      if (tabId === "system") fetchLogs();
    }

    async function checkAuth() {
      try {
        const res = await fetch("/api/guilds", { headers: authHeaders() });
        if (res.status === 401) {
          document.getElementById("authOverlay").style.display = "flex";
        } else {
          document.getElementById("authOverlay").style.display = "none";
          const data = await res.json();
          renderGuilds(data.guilds || []);
          fetchVitals();
        }
      } catch (e) {
        console.error(e);
      }
    }

    function verifyPasskey() {
      passkey = document.getElementById("passkeyInput").value.trim();
      localStorage.setItem("kyomi_passkey", passkey);
      checkAuth();
    }

    function renderGuilds(guilds) {
      const select = document.getElementById("guildSelect");
      select.innerHTML = "";
      if (guilds.length === 0) {
        select.innerHTML = "<option>no guilds found</option>";
        return;
      }
      guilds.forEach(g => {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = `${g.name} (${g.member_count} members)`;
        select.appendChild(opt);
      });
      currentGuildId = guilds[0].id;
      loadGuildData();
    }

    async function fetchVitals() {
      try {
        const res = await fetch("/api/vitals", { headers: authHeaders() });
        if (res.ok) {
          const v = await res.json();
          document.getElementById("vitalPing").textContent = `${v.ping} ms`;
          document.getElementById("vitalUptime").textContent = v.uptime;
          document.getElementById("vitalMembers").textContent = v.members_cached;
          document.getElementById("vitalDbSize").textContent = `${v.db_size_kb} KB`;
        }
      } catch (e) {}
    }

    async function loadGuildData() {
      currentGuildId = document.getElementById("guildSelect").value;
      if (!currentGuildId) return;

      try {
        const res = await fetch(`/api/guild/${currentGuildId}`, { headers: authHeaders() });
        if (!res.ok) return;
        const data = await res.json();

        // Switches
        const s = data.settings || {};
        document.getElementById("sw_automod").checked = s.automod_enabled !== 0;
        document.getElementById("sw_antispam").checked = s.anti_spam_enabled !== 0;
        document.getElementById("sw_ghostping").checked = s.ghostping_enabled !== 0;
        document.getElementById("sw_scam").checked = s.scam_guard_enabled !== 0;
        document.getElementById("sw_invites").checked = s.block_invites_enabled !== 0;
        document.getElementById("sw_links").checked = s.block_links_enabled !== 0;
        document.getElementById("sw_antiraid").checked = s.antiraid_enabled !== 0;

        // Words
        renderWords(data.words || []);

        // Cases
        renderCases(data.cases || []);
      } catch (e) {
        console.error(e);
      }
    }

    function renderWords(words) {
      const cloud = document.getElementById("wordCloud");
      cloud.innerHTML = "";
      if (words.length === 0) {
        cloud.innerHTML = "<div style='font-size: 11px; color: var(--muted);'>no blocked words.</div>";
        return;
      }
      words.forEach(w => {
        const chip = document.createElement("div");
        chip.className = "word-chip";
        chip.innerHTML = `<span>${w}</span><span class="word-del" onclick="deleteWord('${w}')">×</span>`;
        cloud.appendChild(chip);
      });
    }

    function renderCases(cases) {
      const tbody = document.querySelector("#modCasesTable tbody");
      tbody.innerHTML = "";
      if (cases.length === 0) {
        tbody.innerHTML = "<tr><td colspan='3' style='color: var(--muted);'>no recent mod cases.</td></tr>";
        return;
      }
      cases.forEach(c => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><span class="tag">${c.action.toLowerCase()}</span></td>
          <td><span style="color: #fff;">${c.target_id}</span></td>
          <td style="color: var(--muted);">${c.reason || 'n/a'}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function toggleSetting(column, value) {
      await fetch(`/api/guild/${currentGuildId}/setting`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ column, value: value ? 1 : 0 })
      });
    }

    async function addWord() {
      const inp = document.getElementById("newWordInput");
      const word = inp.value.trim();
      if (!word) return;
      await fetch(`/api/guild/${currentGuildId}/words`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ action: "add", word })
      });
      inp.value = "";
      loadGuildData();
    }

    async function deleteWord(word) {
      await fetch(`/api/guild/${currentGuildId}/words`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ action: "remove", word })
      });
      loadGuildData();
    }

    /* TICKETS TAB */
    async function loadTickets() {
      if (!currentGuildId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/tickets`, { headers: authHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById("ticketsTableBody");
        tbody.innerHTML = "";

        const tickets = data.tickets || [];
        document.getElementById("ticketCountBadge").textContent = tickets.filter(t => t.status === "open").length;

        if (tickets.length === 0) {
          tbody.innerHTML = "<tr><td colspan='6' style='color: var(--muted);'>no tickets recorded.</td></tr>";
          return;
        }

        tickets.forEach(t => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>#${String(t.id).padStart(3, '0')}</td>
            <td><code>${t.category}</code></td>
            <td>${t.owner_name} <span style="color: var(--muted);">(${t.owner_id})</span></td>
            <td><span class="tag ${t.status}">${t.status}</span></td>
            <td style="color: var(--muted);">${t.created_at || 'n/a'}</td>
            <td>
              ${t.status !== 'closed' ? `<button class="btn danger" style="padding: 3px 8px; font-size: 10px;" onclick="closeTicket(${t.channel_id})">close</button>` : '<span style="color: var(--muted);">archived</span>'}
            </td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) { console.error(e); }
    }

    async function closeTicket(channelId) {
      if (!confirm("Are you sure you want to close this ticket?")) return;
      await fetch(`/api/guild/${currentGuildId}/ticket/close`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ channel_id: channelId })
      });
      loadTickets();
    }

    /* DOSSIER TAB */
    let currentDossierTargetId = "";
    async function lookupDossier() {
      const q = document.getElementById("dossierSearchInput").value.trim();
      if (!q) return;

      try {
        const res = await fetch(`/api/guild/${currentGuildId}/dossier?query=${encodeURIComponent(q)}`, { headers: authHeaders() });
        if (!res.ok) {
          alert("Member not found.");
          return;
        }
        const d = await res.json();
        currentDossierTargetId = d.id;

        document.getElementById("dossierResult").style.display = "block";
        document.getElementById("dossierAvatar").src = d.avatar_url;
        document.getElementById("dossierName").textContent = d.name;
        document.getElementById("dossierMeta").textContent = `id: ${d.id} · created: ${d.created_at} · joined: ${d.joined_at}`;
        document.getElementById("dossierStanding").textContent = `${d.standing} (${d.trust_score}% trust)`;

        // Strikes
        const strikesDiv = document.getElementById("dossierStrikes");
        if (d.warnings.length === 0) {
          strikesDiv.textContent = "clean record — zero strikes.";
        } else {
          strikesDiv.innerHTML = d.warnings.map(w => `<div>╰ strike #${w.id}: ${w.reason}</div>`).join("");
        }

        // Notes
        renderDossierNotes(d.notes || []);
      } catch (e) {
        console.error(e);
      }
    }

    function renderDossierNotes(notes) {
      const list = document.getElementById("dossierNotesList");
      if (notes.length === 0) {
        list.innerHTML = "<div style='color: var(--muted);'>no staff notes recorded.</div>";
        return;
      }
      list.innerHTML = notes.map(n => `
        <div style="padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03); display: flex; justify-content: space-between;">
          <span>╰ ${n.note}</span>
          <span style="color: var(--muted); cursor: pointer;" onclick="deleteDossierNote(${n.id})">×</span>
        </div>
      `).join("");
    }

    async function addDossierNote() {
      const inp = document.getElementById("newNoteInput");
      const note = inp.value.trim();
      if (!note || !currentDossierTargetId) return;

      await fetch(`/api/guild/${currentGuildId}/dossier/note`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ action: "add", user_id: currentDossierTargetId, note })
      });
      inp.value = "";
      lookupDossier();
    }

    async function deleteDossierNote(noteId) {
      await fetch(`/api/guild/${currentGuildId}/dossier/note`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ action: "delete", note_id: noteId })
      });
      lookupDossier();
    }

    /* SNAPSHOTS TAB */
    async function loadSnapshots() {
      if (!currentGuildId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/snapshots`, { headers: authHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById("snapshotsTableBody");
        tbody.innerHTML = "";

        const snaps = data.snapshots || [];
        if (snaps.length === 0) {
          tbody.innerHTML = "<tr><td colspan='6' style='color: var(--muted);'>no snapshots created yet.</td></tr>";
          return;
        }

        snaps.forEach(s => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>#${String(s.id).padStart(3, '0')}</td>
            <td><strong>${s.label}</strong></td>
            <td>${s.channels_count}</td>
            <td>${s.roles_count}</td>
            <td style="color: var(--muted);">${s.created_at}</td>
            <td>
              <a href="/api/snapshots/${s.id}/download?key=${encodeURIComponent(passkey)}" class="btn" style="padding: 3px 8px; font-size: 10px; text-decoration: none;">download json</a>
            </td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) { console.error(e); }
    }

    async function createWebSnapshot() {
      const label = prompt("Enter a label for this backup:", "web console backup");
      if (!label) return;
      await fetch(`/api/guild/${currentGuildId}/snapshots/create`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ label })
      });
      loadSnapshots();
    }

    /* BUMP TAB */
    async function loadBumpData() {
      if (!currentGuildId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/bump`, { headers: authHeaders() });
        if (!res.ok) return;
        const d = await res.json();

        const timerEl = document.getElementById("bumpTimerVal");
        const descEl = document.getElementById("bumpStatusDesc");

        if (d.remaining_seconds <= 0) {
          timerEl.textContent = "READY";
          timerEl.style.color = "var(--mint)";
          descEl.textContent = "disboard bump is available right now in your server!";
        } else {
          timerEl.style.color = "#fff";
          const m = Math.floor(d.remaining_seconds / 60);
          const s = d.remaining_seconds % 60;
          timerEl.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
          descEl.textContent = "2h cooldown in progress before next bump reminder";
        }

        // Leaderboard
        const tbody = document.getElementById("bumpLeaderboardBody");
        tbody.innerHTML = "";
        const lb = d.leaderboard || [];
        if (lb.length === 0) {
          tbody.innerHTML = "<tr><td colspan='3' style='color: var(--muted);'>no bump stats yet.</td></tr>";
          return;
        }
        lb.forEach((row, i) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>#${i + 1}</td>
            <td>${row.name} <span style="color: var(--muted);">(${row.user_id})</span></td>
            <td><strong>${row.bump_count}</strong> bumps</td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) { console.error(e); }
    }

    /* SYSTEM TAB */
    async function fetchLogs() {
      try {
        const res = await fetch("/logs", { headers: authHeaders() });
        const text = await res.text();
        document.getElementById("terminalLogs").textContent = text;
      } catch (e) {
        document.getElementById("terminalLogs").textContent = "failed to load logs.";
      }
    }

    // Auto-refresh vitals every 10 seconds
    setInterval(fetchVitals, 10000);

    // Initial check
    checkAuth();
  </script>
</body>
</html>
"""


class WebDashboard:
    """Enterprise embedded web dashboard for 303 KYOMI with 5 integrated control modules."""

    def __init__(self, bot: discord.Client, db, port: int = 3030):
        self.bot = bot
        self.db = db
        # Automatically detects Wispbyte/Pterodactyl SERVER_PORT
        self.port = int(os.getenv("PORT", os.getenv("SERVER_PORT", port)))
        self.password = os.getenv("DASHBOARD_PASSWORD", "").strip()
        self.runner: web.AppRunner | None = None

    def _authorized(self, request: web.Request) -> bool:
        if not self.password:
            return True
        header_key = request.headers.get("X-Passkey", "")
        query_key = request.query.get("key", "")
        return (header_key == self.password) or (query_key == self.password)

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
        log_file = "bot.log"
        content = ""
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()[-8000:]
            except Exception as e:
                content = str(e)
        return web.Response(text=content or "no logs yet", content_type="text/plain")

    async def handle_vitals(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)

        ping_ms = round(self.bot.latency * 1000) if self.bot.latency else 0
        now = datetime.datetime.now(datetime.timezone.utc)
        start_t = getattr(self.bot, "start_time", now)
        delta = now - start_t
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

        total_members = sum(g.member_count or 0 for g in self.bot.guilds)
        db_path = getattr(self.db, "db_path", "data/moderation.db")
        db_size_kb = round(os.path.getsize(db_path) / 1024, 1) if os.path.exists(db_path) else 0

        return web.json_response(
            {
                "ping": ping_ms,
                "uptime": uptime_str,
                "members_cached": total_members,
                "db_size_kb": db_size_kb,
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

    # --- 1. TICKETS MODULE ---
    async def handle_get_tickets(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(guild_id)

        raw_tickets = await self.db.get_tickets_for_guild(guild_id)
        results = []
        for t in raw_tickets:
            owner = guild.get_member(t["owner_id"]) if guild else None
            results.append({
                "id": t["id"],
                "channel_id": t["channel_id"],
                "owner_id": t["owner_id"],
                "owner_name": owner.name if owner else f"user_{t['owner_id']}",
                "category": t["category"],
                "claimed_by": t.get("claimed_by"),
                "status": t.get("status", "open"),
                "created_at": t.get("created_at", "n/a"),
            })
        return web.json_response({"tickets": results})

    async def handle_close_ticket(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        body = await request.json()
        ch_id = body.get("channel_id")
        if ch_id:
            await self.db.close_ticket_record(ch_id)
            ch = self.bot.get_channel(ch_id)
            if ch:
                try:
                    await ch.delete(reason="closed via 303 web console")
                except Exception:
                    pass
        return web.json_response({"ok": True})

    # --- 2. DOSSIER & NOTES MODULE ---
    async def handle_dossier(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        query = request.query.get("query", "").strip()

        guild = self.bot.get_guild(guild_id)
        if not guild or not query:
            return web.json_response({"error": "invalid query"}, status=400)

        member: discord.Member | None = None
        if query.isdigit():
            member = guild.get_member(int(query))
        if not member:
            member = discord.utils.get(guild.members, name=query)

        if not member:
            return web.json_response({"error": "member not found"}, status=404)

        from cogs.dossier import calculate_trust_score
        warnings = await self.db.get_warnings(guild.id, member.id)
        notes = await self.db.get_staff_notes(guild.id, member.id)
        cases = await self.db.get_user_mod_cases(guild.id, member.id)
        score, status_tag = calculate_trust_score(member, len(warnings), len(cases))

        return web.json_response({
            "id": str(member.id),
            "name": str(member),
            "avatar_url": member.display_avatar.url,
            "created_at": member.created_at.strftime("%Y-%m-%d"),
            "joined_at": member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "n/a",
            "standing": status_tag,
            "trust_score": score,
            "warnings": warnings,
            "notes": notes,
        })

    async def handle_dossier_note(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        body = await request.json()
        action = body.get("action")

        if action == "add":
            user_id = int(body["user_id"])
            note = body["note"].strip()
            bot_author = self.bot.user.id if self.bot.user else 0
            await self.db.add_staff_note(guild_id, user_id, bot_author, f"[web] {note}")
        elif action == "delete":
            note_id = int(body["note_id"])
            await self.db.delete_staff_note(note_id)

        return web.json_response({"ok": True})

    # --- 3. SNAPSHOTS MODULE ---
    async def handle_get_snapshots(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        snaps = await self.db.get_snapshots(guild_id)
        results = []
        for s in snaps:
            meta = json.loads(s.get("metadata_json") or "{}")
            results.append({
                "id": s["id"],
                "label": s["label"],
                "created_at": s["created_at"],
                "channels_count": meta.get("channels_count", 0),
                "roles_count": meta.get("roles_count", 0),
            })
        return web.json_response({"snapshots": results})

    async def handle_create_snapshot(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return web.json_response({"error": "guild not found"}, status=404)

        body = await request.json()
        label = body.get("label", "web backup")

        from cogs.snapshot import serialize_guild_structure
        roles_data, channels_data, meta = serialize_guild_structure(guild)
        bot_creator = self.bot.user.id if self.bot.user else 0

        snap_id = await self.db.save_snapshot(
            guild.id,
            bot_creator,
            label,
            json.dumps(roles_data),
            json.dumps(channels_data),
            json.dumps(meta),
        )
        return web.json_response({"ok": True, "snapshot_id": snap_id})

    async def handle_download_snapshot(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.Response(text="unauthorized", status=401)
        snap_id = int(request.match_info["snapshot_id"])
        snapshot = await self.db.get_snapshot_by_id(snap_id)
        if not snapshot:
            return web.Response(text="snapshot not found", status=404)

        export_data = {
            "snapshot_id": snapshot["id"],
            "guild_id": snapshot["guild_id"],
            "label": snapshot["label"],
            "created_at": snapshot["created_at"],
            "metadata": json.loads(snapshot["metadata_json"]),
            "roles": json.loads(snapshot["roles_json"]),
            "channels": json.loads(snapshot["channels_json"]),
        }
        json_str = json.dumps(export_data, indent=2)
        headers = {
            "Content-Disposition": f'attachment; filename="303-snapshot-{snap_id:03d}.json"',
            "Content-Type": "application/json",
        }
        return web.Response(text=json_str, headers=headers)

    # --- 4. BUMP MODULE ---
    async def handle_bump_data(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(guild_id)
        settings = await self.db.get_guild_settings(guild_id)
        next_bump = settings.get("next_bump_timestamp") or 0
        now_ts = int(time.time())
        rem_sec = max(0, next_bump - now_ts)

        raw_lb = await self.db.get_bump_leaderboard(guild_id, limit=10)
        leaderboard = []
        for r in raw_lb:
            member = guild.get_member(r["user_id"]) if guild else None
            leaderboard.append({
                "user_id": r["user_id"],
                "name": member.name if member else f"user_{r['user_id']}",
                "bump_count": r["bump_count"],
            })

        return web.json_response({
            "next_bump_timestamp": next_bump,
            "remaining_seconds": rem_sec,
            "leaderboard": leaderboard,
        })

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/", self.handle_index)
        app.router.add_get("/health", self.handle_health)
        app.router.add_get("/logs", self.handle_logs)
        app.router.add_get("/api/vitals", self.handle_vitals)
        app.router.add_get("/api/guilds", self.handle_guilds)
        app.router.add_get("/api/guild/{guild_id}", self.handle_guild_data)
        app.router.add_post("/api/guild/{guild_id}/setting", self.handle_update_setting)
        app.router.add_post("/api/guild/{guild_id}/words", self.handle_words)

        # 5 Modules Routes
        app.router.add_get("/api/guild/{guild_id}/tickets", self.handle_get_tickets)
        app.router.add_post("/api/guild/{guild_id}/ticket/close", self.handle_close_ticket)
        app.router.add_get("/api/guild/{guild_id}/dossier", self.handle_dossier)
        app.router.add_post("/api/guild/{guild_id}/dossier/note", self.handle_dossier_note)
        app.router.add_get("/api/guild/{guild_id}/snapshots", self.handle_get_snapshots)
        app.router.add_post("/api/guild/{guild_id}/snapshots/create", self.handle_create_snapshot)
        app.router.add_get("/api/snapshots/{snapshot_id}/download", self.handle_download_snapshot)
        app.router.add_get("/api/guild/{guild_id}/bump", self.handle_bump_data)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await site.start()

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()
