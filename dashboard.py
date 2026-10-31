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
  <title>KYOMI-303 // OPERATOR CONSOLE</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #070709;
      --surface: #0c0c10;
      --surface-raised: #101015;
      --card: #0f0f14;
      --border: #1a1a22;
      --border-bright: #282836;
      --text: #eaebee;
      --text-dim: #9293a3;
      --muted: #5a5b6a;
      --accent: #8a1c27;
      --accent-bright: #b82534;
      --accent-muted: rgba(138, 28, 39, 0.2);
      --mint: #4ea87d;
      --mint-muted: rgba(78, 168, 125, 0.15);
      --amber: #c5974c;
      --amber-muted: rgba(197, 151, 76, 0.15);
      --mono: 'JetBrains Mono', ui-monospace, monospace;
      --sans: 'Inter', -apple-system, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      background-image:
        linear-gradient(rgba(255, 255, 255, 0.012) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.012) 1px, transparent 1px);
      background-size: 32px 32px;
      color: var(--text);
      font-family: var(--sans);
      min-height: 100vh;
      padding: 16px 20px 48px;
      font-size: 13px;
      line-height: 1.5;
    }

    .container { max-width: 1220px; margin: 0 auto; }

    /* Tactical Auth Modal */
    #authOverlay {
      position: fixed; inset: 0;
      background: rgba(5, 5, 7, 0.94);
      backdrop-filter: blur(8px);
      display: flex; align-items: center; justify-content: center; z-index: 9999;
    }
    .auth-box {
      background: var(--surface);
      border: 1px solid var(--border-bright);
      border-radius: 2px;
      padding: 28px; width: 100%; max-width: 380px;
      box-shadow: 0 24px 60px rgba(0,0,0,0.9);
    }
    .auth-header {
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.1em;
      color: var(--muted);
      margin-bottom: 6px;
      text-transform: uppercase;
    }
    .auth-title {
      font-family: var(--mono);
      font-size: 15px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: #fff;
      margin-bottom: 16px;
    }

    /* Hardware Header */
    .hardware-bar {
      border: 1px solid var(--border);
      background: var(--surface);
      border-radius: 2px;
      padding: 12px 18px;
      margin-bottom: 14px;
      display: flex; align-items: center; justify-content: space-between;
      flex-wrap: wrap; gap: 14px;
    }
    .brand-cluster { display: flex; align-items: center; gap: 14px; }
    .brand-sigil {
      font-family: var(--mono);
      font-weight: 700;
      font-size: 13px;
      background: #15151c;
      border: 1px solid var(--border-bright);
      color: #fff;
      padding: 6px 10px;
      border-radius: 2px;
      letter-spacing: 0.05em;
    }
    .brand-meta { display: flex; flex-direction: column; }
    .brand-title {
      font-family: var(--mono);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.04em;
      color: #fff;
    }
    .brand-sub {
      font-family: var(--mono);
      font-size: 10.5px;
      color: var(--muted);
      letter-spacing: 0.02em;
    }

    .telemetry-pills { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .tag-box {
      font-family: var(--mono);
      font-size: 11px;
      padding: 4px 10px;
      background: #09090d;
      border: 1px solid var(--border);
      border-radius: 2px;
      display: inline-flex; align-items: center; gap: 7px;
      color: var(--text-dim);
    }
    .tag-box.online {
      border-color: rgba(78, 168, 125, 0.4);
      color: var(--mint);
      background: rgba(78, 168, 125, 0.06);
    }
    .indicator-square { width: 6px; height: 6px; background: currentColor; }

    select.node-select {
      background: #09090d;
      color: #fff;
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 6px 12px;
      font-size: 11.5px;
      font-family: var(--mono);
      cursor: pointer;
      outline: none;
    }
    select.node-select:focus { border-color: var(--border-bright); }

    /* Vitals Telemetry Grid */
    .vitals-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 14px;
    }
    @media (max-width: 900px) { .vitals-grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 520px) { .vitals-grid { grid-template-columns: 1fr; } }

    .vital-tile {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 12px 14px;
    }
    .vital-key {
      font-family: var(--mono);
      font-size: 10px;
      color: var(--muted);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 4px;
      display: flex; align-items: center; justify-content: space-between;
    }
    .vital-num {
      font-family: var(--mono);
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }

    /* Terminal Nav Tabs */
    .nav-rack {
      display: flex; gap: 4px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 4px;
      margin-bottom: 14px;
      overflow-x: auto;
    }
    .rack-tab {
      background: transparent;
      border: 1px solid transparent;
      color: var(--muted);
      font-family: var(--mono);
      font-size: 11px;
      padding: 7px 14px;
      border-radius: 2px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.1s;
      letter-spacing: 0.02em;
    }
    .rack-tab:hover { color: var(--text); background: #111117; }
    .rack-tab.active {
      color: #fff;
      background: #14141c;
      border-color: var(--border-bright);
      font-weight: 600;
    }

    /* Panes */
    .pane { display: none; }
    .pane.active { display: block; }

    /* Industrial Panel Cards */
    .panel-block {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 18px;
      margin-bottom: 14px;
    }
    .panel-header {
      display: flex; align-items: center; justify-content: space-between;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
      margin-bottom: 14px;
    }
    .panel-headline {
      font-family: var(--mono);
      font-size: 11.5px;
      font-weight: 600;
      letter-spacing: 0.06em;
      color: #fff;
      text-transform: uppercase;
      display: flex; align-items: center; gap: 8px;
    }

    /* Density Grid */
    .grid-duo {
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 14px;
    }
    @media (max-width: 900px) { .grid-duo { grid-template-columns: 1fr; } }

    /* Utilitarian Setting Row */
    .op-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.025);
    }
    .op-row:last-child { border-bottom: none; }
    .op-label { font-size: 12.5px; font-weight: 500; color: #fff; }
    .op-desc { font-size: 11px; color: var(--muted); font-family: var(--mono); }

    /* Hardware Rocker Switches */
    .rocker {
      display: inline-flex;
      background: #09090d;
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 2px;
      cursor: pointer;
      font-family: var(--mono);
      font-size: 10.5px;
      user-select: none;
    }
    .rocker-btn {
      padding: 4px 10px;
      border-radius: 2px;
      color: var(--muted);
      transition: all 0.1s;
    }
    .rocker[data-state="on"] .btn-on {
      background: var(--accent);
      color: #fff;
      font-weight: 600;
    }
    .rocker[data-state="off"] .btn-off {
      background: #181820;
      color: var(--text-dim);
      font-weight: 600;
    }

    /* Inputs & Buttons */
    input[type="text"], input[type="password"], input[type="number"], select.input-ctrl {
      background: #08080b;
      border: 1px solid var(--border);
      border-radius: 2px;
      color: #fff;
      padding: 7px 11px;
      font-size: 12px;
      font-family: var(--mono);
      outline: none;
    }
    input[type="text"]:focus, input[type="password"]:focus, select.input-ctrl:focus {
      border-color: var(--border-bright);
    }
    .ctrl-btn {
      background: #121218;
      border: 1px solid var(--border);
      border-radius: 2px;
      color: #fff;
      padding: 7px 13px;
      font-size: 11.5px;
      font-family: var(--mono);
      cursor: pointer;
      display: inline-flex; align-items: center; gap: 6px;
      letter-spacing: 0.02em;
      transition: all 0.1s;
    }
    .ctrl-btn:hover { background: #1a1a24; border-color: var(--border-bright); }
    .ctrl-btn.armed { background: var(--accent); border-color: var(--accent-bright); color: #fff; font-weight: 600; }
    .ctrl-btn.armed:hover { background: var(--accent-bright); }

    /* Tables */
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      font-family: var(--mono);
      font-size: 11.5px;
    }
    table.data-table th {
      text-align: left;
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      padding: 8px 10px;
      border-bottom: 1px solid var(--border);
    }
    table.data-table td {
      padding: 9px 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.02);
      color: var(--text-dim);
    }
    table.data-table tr:hover td {
      background: rgba(255, 255, 255, 0.015);
      color: #fff;
    }

    /* Monochrome Status Chips */
    .chip {
      font-family: var(--mono);
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 2px;
      background: #111116;
      border: 1px solid var(--border);
      color: var(--text-dim);
      display: inline-block;
    }
    .chip.green { border-color: rgba(78, 168, 125, 0.4); color: var(--mint); background: var(--mint-muted); }
    .chip.amber { border-color: rgba(197, 151, 76, 0.4); color: var(--amber); background: var(--amber-muted); }
    .chip.red { border-color: rgba(184, 37, 52, 0.4); color: #ff8590; background: var(--accent-muted); }

    /* Word Cloud */
    .word-matrix { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
    .word-unit {
      background: #09090d;
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 3px 8px;
      font-size: 11px;
      font-family: var(--mono);
      display: inline-flex; align-items: center; gap: 6px;
    }
    .word-x { cursor: pointer; color: var(--muted); }
    .word-x:hover { color: #ff6070; }

    /* Raw Terminal Screen */
    .screen-box {
      background: #050507;
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 14px;
      font-family: var(--mono);
      font-size: 11px;
      line-height: 1.6;
      color: #a4a5b4;
      max-height: 380px;
      overflow-y: auto;
      white-space: pre-wrap;
    }

    /* Notification Banner */
    #actionBanner {
      position: fixed; bottom: 20px; right: 20px;
      background: #111118; border: 1px solid var(--border-bright);
      padding: 10px 16px; border-radius: 2px;
      font-family: var(--mono); font-size: 11.5px;
      color: #fff; z-index: 999; display: none;
      box-shadow: 0 10px 30px rgba(0,0,0,0.8);
    }
  </style>
</head>
<body>

  <!-- Auth Passkey Screen -->
  <div id="authOverlay" style="display: none;">
    <div class="auth-box">
      <div class="auth-header">KYOMI-303 // ACCESS GATE</div>
      <div class="auth-title">OPERATOR AUTHENTICATION</div>
      <input type="password" id="passkeyInput" placeholder="ENTER ACCESS KEY..." style="width: 100%; margin-bottom: 12px;">
      <button class="ctrl-btn armed" style="width: 100%; justify-content: center;" onclick="verifyPasskey()">VERIFY CREDENTIALS</button>
    </div>
  </div>

  <div id="actionBanner"></div>

  <div class="container">
    <!-- Top Hardware Header -->
    <header class="hardware-bar">
      <div class="brand-cluster">
        <div class="brand-sigil">303</div>
        <div class="brand-meta">
          <div class="brand-title">KYOMI // OPERATOR CONSOLE</div>
          <div class="brand-sub">CORE DAEMON v2.5.0 &bull; MONOCHROME SUBSYSTEM</div>
        </div>
      </div>
      <div class="telemetry-pills">
        <div class="tag-box online" id="statusPill">
          <div class="indicator-square"></div>
          <span id="statusText">DAEMON ARMED</span>
        </div>
        <div class="tag-box">
          <span>TARGET:</span>
          <select class="node-select" id="guildSelect" onchange="loadGuildData()">
            <option value="">LOADING CLUSTER...</option>
          </select>
        </div>
      </div>
    </header>

    <!-- Vitals Telemetry Row -->
    <div class="vitals-grid">
      <div class="vital-tile">
        <div class="vital-key"><span>WS HEARTBEAT</span><span>PING</span></div>
        <div class="vital-num" id="vital_ping">-- ms</div>
      </div>
      <div class="vital-tile">
        <div class="vital-key"><span>UPTIME CADENCE</span><span>RUN</span></div>
        <div class="vital-num" id="vital_uptime">--</div>
      </div>
      <div class="vital-tile">
        <div class="vital-key"><span>MEMBER CACHE</span><span>POP</span></div>
        <div class="vital-num" id="vital_members">--</div>
      </div>
      <div class="vital-tile">
        <div class="vital-key"><span>SQLITE FOOTPRINT</span><span>DISK</span></div>
        <div class="vital-num" id="vital_dbsize">-- KB</div>
      </div>
    </div>

    <!-- Navigation Rack -->
    <nav class="nav-rack">
      <button class="rack-tab active" onclick="switchPane('automod', event)">01 // AUTOMOD</button>
      <button class="rack-tab" onclick="switchPane('tickets', event)">02 // TICKETS</button>
      <button class="rack-tab" onclick="switchPane('dossier', event)">03 // DOSSIER</button>
      <button class="rack-tab" onclick="switchPane('vanity', event)">04 // VANITY TRACKER</button>
      <button class="rack-tab" onclick="switchPane('snapshots', event)">05 // SNAPSHOTS</button>
      <button class="rack-tab" onclick="switchPane('bumping', event)">06 // DISBOARD</button>
      <button class="rack-tab" onclick="switchPane('system', event)">07 // CONSOLE LOGS</button>
    </nav>

    <!-- PANE 1: AUTOMOD -->
    <section id="pane-automod" class="pane active">
      <div class="grid-duo">
        <div class="panel-block">
          <div class="panel-header">
            <div class="panel-headline">RULESET CONFIGURATION</div>
            <span class="chip green">SYSTEM LIVE</span>
          </div>

          <div class="op-row">
            <div>
              <div class="op-label">Master AutoMod Defense</div>
              <div class="op-desc">Global security filter and enforcement pipeline</div>
            </div>
            <div class="rocker" id="rocker_automod" onclick="toggleRocker('automod_enabled', this)">
              <span class="rocker-btn btn-on">ON</span>
              <span class="rocker-btn btn-off">OFF</span>
            </div>
          </div>

          <div class="op-row">
            <div>
              <div class="op-label">Anti-Spam Rate Gate</div>
              <div class="op-desc">Velocity detection (5 messages / 5 seconds threshold)</div>
            </div>
            <div class="rocker" id="rocker_antispam" onclick="toggleRocker('anti_spam_enabled', this)">
              <span class="rocker-btn btn-on">ON</span>
              <span class="rocker-btn btn-off">OFF</span>
            </div>
          </div>

          <div class="op-row">
            <div>
              <div class="op-label">Anti-Raid Ingress Shield</div>
              <div class="op-desc">Rejects raid waves and unverified burner accounts</div>
            </div>
            <div class="rocker" id="rocker_antiraid" onclick="toggleRocker('antiraid_enabled', this)">
              <span class="rocker-btn btn-on">ON</span>
              <span class="rocker-btn btn-off">OFF</span>
            </div>
          </div>

          <div class="op-row">
            <div>
              <div class="op-label">Anti-Ghostping Monitor</div>
              <div class="op-desc">Intercepts and exposes deleted mention alerts</div>
            </div>
            <div class="rocker" id="rocker_ghostping" onclick="toggleRocker('ghostping_enabled', this)">
              <span class="rocker-btn btn-on">ON</span>
              <span class="rocker-btn btn-off">OFF</span>
            </div>
          </div>

          <div class="op-row">
            <div>
              <div class="op-label">Anti-Invite Quarantine</div>
              <div class="op-desc">Purges unauthorized Discord server invites</div>
            </div>
            <div class="rocker" id="rocker_invites" onclick="toggleRocker('block_invites', this)">
              <span class="rocker-btn btn-on">ON</span>
              <span class="rocker-btn btn-off">OFF</span>
            </div>
          </div>

          <div class="op-row">
            <div>
              <div class="op-label">Anti-Link Filter</div>
              <div class="op-desc">Strips unauthorized external URLs from chat</div>
            </div>
            <div class="rocker" id="rocker_links" onclick="toggleRocker('block_links', this)">
              <span class="rocker-btn btn-on">ON</span>
              <span class="rocker-btn btn-off">OFF</span>
            </div>
          </div>
        </div>

        <div>
          <!-- Word Filter Block -->
          <div class="panel-block">
            <div class="panel-header">
              <div class="panel-headline">BLACKLISTED PATTERNS</div>
            </div>
            <div style="display: flex; gap: 6px; margin-bottom: 12px;">
              <input type="text" id="newWordInput" placeholder="ADD PHRASE / PATTERN..." style="flex: 1;">
              <button class="ctrl-btn armed" onclick="addFilterWord()">+ ADD</button>
            </div>
            <div class="word-matrix" id="wordMatrix">
              <span class="chip">NO PATTERNS ARMED</span>
            </div>
          </div>

          <!-- Mod Cases Snippet -->
          <div class="panel-block">
            <div class="panel-header">
              <div class="panel-headline">RECENT DISCIPLINARY LOGS</div>
            </div>
            <table class="data-table">
              <thead>
                <tr>
                  <th>CASE</th>
                  <th>ACTION</th>
                  <th>TARGET</th>
                  <th>REASON</th>
                </tr>
              </thead>
              <tbody id="modCasesBody">
                <tr><td colspan="4" style="color: var(--muted); text-align: center;">NO RECENT INFRACTIONS</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- PANE 2: TICKETS -->
    <section id="pane-tickets" class="pane">
      <div class="panel-block">
        <div class="panel-header">
          <div class="panel-headline">ACTIVE & ARCHIVED TICKET REGISTRY</div>
          <button class="ctrl-btn" onclick="loadTickets()">REFRESH FEED</button>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>CHANNEL</th>
              <th>OPENER</th>
              <th>TOPIC</th>
              <th>STATE</th>
              <th>OPENED</th>
              <th>COMMAND</th>
            </tr>
          </thead>
          <tbody id="ticketsBody">
            <tr><td colspan="7" style="text-align: center; color: var(--muted);">FETCHING ACTIVE ROOMS...</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- PANE 3: DOSSIER -->
    <section id="pane-dossier" class="pane">
      <div class="panel-block">
        <div class="panel-header">
          <div class="panel-headline">MEMBER INTELLIGENCE & DOSSIER SEARCH</div>
        </div>
        <div style="display: flex; gap: 8px; margin-bottom: 14px;">
          <input type="text" id="dossierQuery" placeholder="USER ID OR USERNAME..." style="flex: 1;">
          <button class="ctrl-btn armed" onclick="searchDossier()">RETRIEVE DOSSIER</button>
        </div>

        <div id="dossierResult" style="display: none;">
          <div class="grid-duo">
            <div class="panel-block" style="background: #09090d;">
              <div style="display: flex; gap: 14px; align-items: center; margin-bottom: 14px;">
                <img id="dos_avatar" src="" style="width: 44px; height: 44px; border: 1px solid var(--border); border-radius: 2px;">
                <div>
                  <div id="dos_name" style="font-size: 15px; font-weight: 700; color: #fff; font-family: var(--mono);">--</div>
                  <div id="dos_id" style="font-size: 11px; color: var(--muted); font-family: var(--mono);">--</div>
                </div>
              </div>
              <div class="op-row">
                <span class="op-desc">SECURITY STANDING</span>
                <span id="dos_standing" class="chip">--</span>
              </div>
              <div class="op-row">
                <span class="op-desc">JOIN DATE</span>
                <span id="dos_joined" style="font-family: var(--mono); color: #fff;">--</span>
              </div>
              <div class="op-row">
                <span class="op-desc">CREATION DATE</span>
                <span id="dos_created" style="font-family: var(--mono); color: #fff;">--</span>
              </div>
              <div class="op-row">
                <span class="op-desc">STRIKES (WARNS)</span>
                <span id="dos_strikes" style="font-family: var(--mono); color: #fff; font-weight: 700;">0</span>
              </div>
            </div>

            <div class="panel-block" style="background: #09090d;">
              <div class="panel-headline" style="margin-bottom: 10px;">STAFF DOSSIER NOTES</div>
              <div style="display: flex; gap: 6px; margin-bottom: 12px;">
                <input type="text" id="dos_note_input" placeholder="RECORD STAFF OBSERVATION..." style="flex: 1;">
                <button class="ctrl-btn armed" onclick="addDossierNote()">RECORD</button>
              </div>
              <div id="dos_notes_list" style="max-height: 180px; overflow-y: auto;">
                <div style="color: var(--muted); font-family: var(--mono); font-size: 11px;">NO STAFF NOTES ON RECORD</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- PANE 4: VANITY TRACKER -->
    <section id="pane-vanity" class="pane">
      <div class="grid-duo">
        <div class="panel-block">
          <div class="panel-header">
            <div class="panel-headline">VANITY STATUS DAEMON</div>
            <span class="chip" id="vnt_status_chip">CHECKING</span>
          </div>

          <div class="op-row">
            <div>
              <div class="op-label">Tracker State</div>
              <div class="op-desc">Real-time presence listener & auto-role assignment</div>
            </div>
            <div class="rocker" id="rocker_vanity" onclick="toggleRocker('vanity_enabled', this)">
              <span class="rocker-btn btn-on">ON</span>
              <span class="rocker-btn btn-off">OFF</span>
            </div>
          </div>

          <div style="margin-top: 14px;">
            <div class="op-desc" style="margin-bottom: 4px;">TARGET VANITY PHRASE</div>
            <div style="display: flex; gap: 6px;">
              <input type="text" id="vnt_phrase_input" placeholder="e.g. .gg/303 or /303" style="flex: 1;">
              <button class="ctrl-btn" onclick="saveVanityPhrase()">SAVE PHRASE</button>
            </div>
          </div>

          <div style="margin-top: 14px;">
            <div class="op-desc" style="margin-bottom: 4px;">ASSIGNED SUPPORTER ROLE (ID)</div>
            <input type="text" id="vnt_role_input" placeholder="ROLE ID..." style="width: 100%; margin-bottom: 6px;">
            <button class="ctrl-btn" onclick="saveVanityRole()">LINK ROLE</button>
          </div>

          <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border);">
            <button class="ctrl-btn armed" style="width: 100%; justify-content: center;" onclick="triggerVanityScan()">
              ◈ SCAN & SYNC ALL CACHED MEMBERS NOW
            </button>
          </div>
        </div>

        <div class="panel-block">
          <div class="panel-header">
            <div class="panel-headline">ACTIVE SUPPORTERS ROSTER</div>
            <span class="chip green" id="vnt_count_chip">0 SUPPORTERS</span>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th>SUPPORTER</th>
                <th>DETECTED STATUS</th>
                <th>SINCE</th>
              </tr>
            </thead>
            <tbody id="vnt_supporters_body">
              <tr><td colspan="3" style="text-align: center; color: var(--muted);">NO DETECTED SUPPORTERS</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- PANE 5: SNAPSHOTS -->
    <section id="pane-snapshots" class="pane">
      <div class="panel-block">
        <div class="panel-header">
          <div class="panel-headline">SERVER STRUCTURE BACKUP VAULT</div>
          <button class="ctrl-btn armed" onclick="createSnapshotWeb()">+ CREATE STRUCTURE SNAPSHOT</button>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>LABEL</th>
              <th>ROLES</th>
              <th>CHANNELS</th>
              <th>CATEGORIES</th>
              <th>DATE</th>
              <th>EXPORT</th>
            </tr>
          </thead>
          <tbody id="snapshotsBody">
            <tr><td colspan="7" style="text-align: center; color: var(--muted);">LOADING BACKUP VAULT...</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- PANE 6: DISBOARD -->
    <section id="pane-bumping" class="pane">
      <div class="grid-duo">
        <div class="panel-block">
          <div class="panel-header">
            <div class="panel-headline">2-HOUR CADENCE COUNTER</div>
          </div>
          <div style="text-align: center; padding: 28px 10px;">
            <div style="font-family: var(--mono); font-size: 11px; color: var(--muted); margin-bottom: 6px;">NEXT DISBOARD WINDOW OPENS IN</div>
            <div id="bumpCountdown" style="font-family: var(--mono); font-size: 38px; font-weight: 700; color: #fff;">00:00:00</div>
            <div id="bumpStatusNotice" style="font-family: var(--mono); font-size: 11px; color: var(--mint); margin-top: 8px;">WINDOW READY</div>
          </div>
        </div>

        <div class="panel-block">
          <div class="panel-header">
            <div class="panel-headline">SERVER BUMP LEADERBOARD</div>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>RANK</th>
                <th>BUMPER</th>
                <th>SUCCESSFUL BUMPS</th>
              </tr>
            </thead>
            <tbody id="bumpLeaderboardBody">
              <tr><td colspan="3" style="text-align: center; color: var(--muted);">NO BUMPS LOGGED</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- PANE 7: CONSOLE LOGS -->
    <section id="pane-system" class="pane">
      <div class="panel-block">
        <div class="panel-header">
          <div class="panel-headline">DAEMON CONSOLE TELEMETRY STREAM</div>
          <button class="ctrl-btn" onclick="fetchLogs()">FETCH RAW LOG</button>
        </div>
        <div class="screen-box" id="terminalScreen">INITIALIZING TERMINAL BUFFER...</div>
      </div>
    </section>
  </div>

  <script>
    let currentGuildId = "";
    let cachedWords = [];
    let passkey = localStorage.getItem("kyomi_passkey") || "";

    function authHeaders() {
      return { "X-Passkey": passkey, "Content-Type": "application/json" };
    }

    function showBanner(msg, isError = false) {
      const b = document.getElementById("actionBanner");
      b.textContent = msg;
      b.style.borderColor = isError ? "var(--accent-bright)" : "var(--border-bright)";
      b.style.display = "block";
      setTimeout(() => { b.style.display = "none"; }, 3200);
    }

    function switchPane(paneId, ev) {
      document.querySelectorAll(".pane").forEach(el => el.classList.remove("active"));
      document.querySelectorAll(".rack-tab").forEach(el => el.classList.remove("active"));
      const target = document.getElementById("pane-" + paneId);
      if (target) target.classList.add("active");
      if (ev && ev.currentTarget) ev.currentTarget.classList.add("active");

      if (paneId === "tickets") loadTickets();
      if (paneId === "vanity") loadVanity();
      if (paneId === "snapshots") loadSnapshots();
      if (paneId === "bumping") loadBumpData();
      if (paneId === "system") fetchLogs();
    }

    async function checkAuth() {
      try {
        const res = await fetch("/api/guilds", { headers: authHeaders() });
        if (res.status === 401) {
          document.getElementById("authOverlay").style.display = "flex";
        } else {
          document.getElementById("authOverlay").style.display = "none";
          const data = await res.json();
          renderGuildSelect(data.guilds || []);
          startTelemetryLoop();
        }
      } catch (e) {
        console.error("Auth check failed:", e);
      }
    }

    async function verifyPasskey() {
      const val = document.getElementById("passkeyInput").value.trim();
      passkey = val;
      localStorage.setItem("kyomi_passkey", val);
      await checkAuth();
    }

    function renderGuildSelect(guilds) {
      const sel = document.getElementById("guildSelect");
      sel.innerHTML = "";
      if (!guilds || guilds.length === 0) {
        sel.innerHTML = '<option value="">NO CLUSTERS ATTACHED</option>';
        return;
      }
      guilds.forEach((g, i) => {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = `${g.name} (${g.id})`;
        if (i === 0) opt.selected = true;
        sel.appendChild(opt);
      });
      loadGuildData();
    }

    async function loadGuildData() {
      currentGuildId = document.getElementById("guildSelect").value;
      if (!currentGuildId) return;

      try {
        const res = await fetch(`/api/guild/${currentGuildId}`, { headers: authHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const s = data.settings || {};

        setRockerState("rocker_automod", s.automod_enabled !== 0);
        setRockerState("rocker_antispam", s.anti_spam_enabled !== 0);
        setRockerState("rocker_antiraid", s.antiraid_enabled !== 0);
        setRockerState("rocker_ghostping", s.ghostping_enabled !== 0);
        setRockerState("rocker_invites", s.block_invites !== 0);
        setRockerState("rocker_links", s.block_links !== 0);
        setRockerState("rocker_vanity", s.vanity_enabled === 1);

        renderWords(data.words || []);
        renderModCases(data.cases || []);
      } catch (e) {
        console.error(e);
      }
    }

    function setRockerState(rockerId, isArmed) {
      const el = document.getElementById(rockerId);
      if (el) el.setAttribute("data-state", isArmed ? "on" : "off");
    }

    async function toggleRocker(settingKey, el) {
      const currentState = el.getAttribute("data-state") === "on";
      const nextVal = currentState ? 0 : 1;
      el.setAttribute("data-state", nextVal ? "on" : "off");

      try {
        const res = await fetch(`/api/guild/${currentGuildId}/setting`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ key: settingKey, value: nextVal })
        });
        if (res.ok) showBanner(`SETTING UPDATED: ${settingKey} -> ${nextVal ? 'ARMED' : 'DISABLED'}`);
      } catch (e) {
        showBanner("FAILED TO PERSIST SETTING", true);
      }
    }

    function renderWords(words) {
      cachedWords = words;
      const matrix = document.getElementById("wordMatrix");
      matrix.innerHTML = "";
      if (!words || words.length === 0) {
        matrix.innerHTML = '<span class="chip">NO PATTERNS ARMED</span>';
        return;
      }
      words.forEach(w => {
        const unit = document.createElement("div");
        unit.className = "word-unit";
        unit.innerHTML = `<span>${escapeHtml(w)}</span><span class="word-x" onclick="deleteWord('${escapeHtml(w)}')">&times;</span>`;
        matrix.appendChild(unit);
      });
    }

    async function addFilterWord() {
      const inp = document.getElementById("newWordInput");
      const word = inp.value.trim();
      if (!word) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/words`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ action: "add", word })
        });
        if (res.ok) {
          inp.value = "";
          showBanner(`ARMED FILTER PATTERN: ${word}`);
          loadGuildData();
        }
      } catch (e) { showBanner("WORD REGISTRATION FAILED", true); }
    }

    async function deleteWord(word) {
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/words`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ action: "remove", word })
        });
        if (res.ok) {
          showBanner(`PURGED PATTERN: ${word}`);
          loadGuildData();
        }
      } catch (e) { showBanner("WORD REMOVAL FAILED", true); }
    }

    function renderModCases(cases) {
      const tbody = document.getElementById("modCasesBody");
      tbody.innerHTML = "";
      if (!cases || cases.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="color: var(--muted); text-align: center;">NO RECENT INFRACTIONS</td></tr>';
        return;
      }
      cases.forEach(c => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>#${c.id}</td>
          <td><span class="chip red">${c.action.toUpperCase()}</span></td>
          <td>${c.target_id}</td>
          <td>${escapeHtml(c.reason || 'NONE RECORDED')}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function startTelemetryLoop() {
      const poll = async () => {
        try {
          const res = await fetch("/api/vitals", { headers: authHeaders() });
          if (res.ok) {
            const v = await res.json();
            document.getElementById("vital_ping").textContent = v.ping_ms + " ms";
            document.getElementById("vital_uptime").textContent = v.uptime;
            document.getElementById("vital_members").textContent = v.cached_members;
            document.getElementById("vital_dbsize").textContent = v.db_size_kb + " KB";
          }
        } catch (e) {}
      };
      poll();
      setInterval(poll, 8000);
    }

    // --- TICKETS ---
    async function loadTickets() {
      if (!currentGuildId) return;
      const tbody = document.getElementById("ticketsBody");
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/tickets`, { headers: authHeaders() });
        const list = await res.json();
        tbody.innerHTML = "";
        if (!list || list.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--muted);">NO ACTIVE ROOMS LOGGED</td></tr>';
          return;
        }
        list.forEach(t => {
          const tr = document.createElement("tr");
          const stateColor = t.status === "open" ? "green" : (t.status === "archived" ? "amber" : "");
          tr.innerHTML = `
            <td>#${t.id}</td>
            <td><code>${escapeHtml(t.channel_name || t.channel_id)}</code></td>
            <td>${escapeHtml(t.owner_name || t.owner_id)}</td>
            <td><span class="chip">${escapeHtml(t.category)}</span></td>
            <td><span class="chip ${stateColor}">${t.status.toUpperCase()}</span></td>
            <td>${t.created_at ? t.created_at.slice(0, 16) : '--'}</td>
            <td>
              ${t.status !== 'closed' ? `<button class="ctrl-btn" style="padding: 3px 8px;" onclick="closeTicketRemote(${t.channel_id})">TERMINATE</button>` : '--'}
            </td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--muted);">TICKETS TELEMETRY OFFLINE</td></tr>';
      }
    }

    async function closeTicketRemote(channelId) {
      if (!confirm("TERMINATE TICKET ROOM AND SAVE AUDIT LOG?")) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/ticket/close`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ channel_id: channelId })
        });
        if (res.ok) {
          showBanner("TICKET TERMINATION COMMENCED");
          loadTickets();
        }
      } catch (e) { showBanner("REMOTE TERMINATION FAILED", true); }
    }

    // --- DOSSIER ---
    let currentDossierUserId = null;
    async function searchDossier() {
      const q = document.getElementById("dossierQuery").value.trim();
      if (!q || !currentGuildId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/dossier?query=${encodeURIComponent(q)}`, { headers: authHeaders() });
        if (!res.ok) return showBanner("MEMBER RECORD NOT FOUND", true);
        const data = await res.json();
        currentDossierUserId = data.user_id;

        document.getElementById("dos_name").textContent = data.name;
        document.getElementById("dos_id").textContent = `ID: ${data.user_id}`;
        document.getElementById("dos_avatar").src = data.avatar_url || "https://cdn.discordapp.com/embed/avatars/0.png";
        document.getElementById("dos_standing").textContent = (data.standing || "CLEAN").toUpperCase();
        document.getElementById("dos_standing").className = "chip " + (data.standing === "trusted" ? "green" : (data.standing === "flagged" ? "red" : "amber"));
        document.getElementById("dos_joined").textContent = data.joined_at || "--";
        document.getElementById("dos_created").textContent = data.created_at || "--";
        document.getElementById("dos_strikes").textContent = data.strikes || 0;

        renderDossierNotes(data.notes || []);
        document.getElementById("dossierResult").style.display = "block";
      } catch (e) { showBanner("DOSSIER LOOKUP FAILED", true); }
    }

    function renderDossierNotes(notes) {
      const container = document.getElementById("dos_notes_list");
      container.innerHTML = "";
      if (!notes || notes.length === 0) {
        container.innerHTML = '<div style="color: var(--muted); font-family: var(--mono); font-size: 11px;">NO STAFF OBSERVATIONS RECORDED</div>';
        return;
      }
      notes.forEach(n => {
        const item = document.createElement("div");
        item.style.padding = "6px 0";
        item.style.borderBottom = "1px solid rgba(255,255,255,0.025)";
        item.innerHTML = `
          <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--muted); font-family: var(--mono);">
            <span>BY: ${n.author_id}</span>
            <span>${n.created_at}</span>
          </div>
          <div style="font-size: 12px; color: #fff; margin-top: 2px;">${escapeHtml(n.note)}</div>
        `;
        container.appendChild(item);
      });
    }

    async function addDossierNote() {
      const inp = document.getElementById("dos_note_input");
      const note = inp.value.trim();
      if (!note || !currentDossierUserId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/dossier/note`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ user_id: currentDossierUserId, note })
        });
        if (res.ok) {
          inp.value = "";
          showBanner("STAFF OBSERVATION LOGGED");
          searchDossier();
        }
      } catch (e) { showBanner("NOTE RECORDING FAILED", true); }
    }

    // --- VANITY TRACKER ---
    async function loadVanity() {
      if (!currentGuildId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/vanity`, { headers: authHeaders() });
        if (!res.ok) return;
        const v = await res.json();

        setRockerState("rocker_vanity", v.enabled);
        const chip = document.getElementById("vnt_status_chip");
        chip.textContent = v.enabled ? "TRACKER LIVE" : "DISABLED";
        chip.className = "chip " + (v.enabled ? "green" : "");

        document.getElementById("vnt_phrase_input").value = v.phrase || ".gg/303";
        document.getElementById("vnt_role_input").value = v.role_id || "";
        document.getElementById("vnt_count_chip").textContent = `${v.count} SUPPORTERS`;

        const tbody = document.getElementById("vnt_supporters_body");
        tbody.innerHTML = "";
        if (!v.supporters || v.supporters.length === 0) {
          tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--muted);">NO DETECTED SUPPORTERS</td></tr>';
          return;
        }
        v.supporters.forEach(s => {
          const tr = document.createElement("tr");
          const dateStr = s.detected_at ? new Date(s.detected_at * 1000).toISOString().slice(0, 16) : '--';
          tr.innerHTML = `
            <td><code>${escapeHtml(s.name)}</code> (${s.user_id})</td>
            <td><code>${escapeHtml(s.status_text || '--')}</code></td>
            <td>${dateStr}</td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) { console.error(e); }
    }

    async function saveVanityPhrase() {
      const phrase = document.getElementById("vnt_phrase_input").value.trim();
      if (!phrase) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/setting`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ key: "vanity_phrase", value: phrase })
        });
        if (res.ok) showBanner(`ARMED VANITY PHRASE: ${phrase}`);
      } catch (e) { showBanner("PHRASE SAVE FAILED", true); }
    }

    async function saveVanityRole() {
      const roleId = document.getElementById("vnt_role_input").value.trim();
      if (!roleId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/setting`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ key: "vanity_role_id", value: parseInt(roleId) })
        });
        if (res.ok) showBanner(`LINKED SUPPORTER ROLE: ${roleId}`);
      } catch (e) { showBanner("ROLE SAVE FAILED", true); }
    }

    async function triggerVanityScan() {
      showBanner("SCANNING GUILD MEMBERS...");
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/vanity/scan`, {
          method: "POST",
          headers: authHeaders()
        });
        if (res.ok) {
          const r = await res.json();
          showBanner(`SCAN COMPLETE: ${r.scanned} SCANNED, ${r.awarded} AWARDED, ${r.revoked} REVOKED`);
          loadVanity();
        } else {
          showBanner("SCAN EXECUTION FAILED", true);
        }
      } catch (e) { showBanner("SCAN DISPATCH FAILED", true); }
    }

    // --- SNAPSHOTS ---
    async function loadSnapshots() {
      if (!currentGuildId) return;
      const tbody = document.getElementById("snapshotsBody");
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/snapshots`, { headers: authHeaders() });
        const list = await res.json();
        tbody.innerHTML = "";
        if (!list || list.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--muted);">NO SNAPSHOTS IN VAULT</td></tr>';
          return;
        }
        list.forEach(s => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>#${s.id}</td>
            <td><code>${escapeHtml(s.label)}</code></td>
            <td>${s.roles_count}</td>
            <td>${s.channels_count}</td>
            <td>${s.categories_count}</td>
            <td>${s.created_at}</td>
            <td>
              <a href="/api/snapshots/${s.id}/download?key=${encodeURIComponent(passkey)}" class="ctrl-btn" style="padding: 3px 8px; text-decoration: none;">EXPORT JSON</a>
            </td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) { tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--muted);">SNAPSHOT VAULT OFFLINE</td></tr>'; }
    }

    async function createSnapshotWeb() {
      const label = prompt("ENTER STRUCTURE SNAPSHOT LABEL:", "web-checkpoint");
      if (!label) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/snapshots/create`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ label })
        });
        if (res.ok) {
          showBanner("SNAPSHOT SECURED IN VAULT");
          loadSnapshots();
        }
      } catch (e) { showBanner("CREATION FAILED", true); }
    }

    // --- BUMP DATA ---
    let bumpTimerInterval = null;
    async function loadBumpData() {
      if (!currentGuildId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/bump`, { headers: authHeaders() });
        if (!res.ok) return;
        const d = await res.json();

        let rem = d.remaining_seconds || 0;
        const renderTimer = () => {
          if (rem <= 0) {
            document.getElementById("bumpCountdown").textContent = "READY";
            document.getElementById("bumpCountdown").style.color = "var(--mint)";
            document.getElementById("bumpStatusNotice").textContent = "DISBOARD CADENCE READY TO FIRE";
          } else {
            const h = Math.floor(rem / 3600);
            const m = Math.floor((rem % 3600) / 60);
            const s = rem % 60;
            document.getElementById("bumpCountdown").textContent =
              `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
            document.getElementById("bumpCountdown").style.color = "#fff";
            document.getElementById("bumpStatusNotice").textContent = "WINDOW LOCKED IN 2H CADENCE";
            rem--;
          }
        };
        clearInterval(bumpTimerInterval);
        renderTimer();
        bumpTimerInterval = setInterval(renderTimer, 1000);

        const tbody = document.getElementById("bumpLeaderboardBody");
        tbody.innerHTML = "";
        if (!d.leaderboard || d.leaderboard.length === 0) {
          tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--muted);">NO BUMPS LOGGED</td></tr>';
          return;
        }
        d.leaderboard.forEach((r, idx) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><code>#${idx+1}</code></td>
            <td>${escapeHtml(r.name)}</td>
            <td><strong>${r.bump_count}</strong></td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) { console.error(e); }
    }

    // --- LOGS ---
    async function fetchLogs() {
      const scr = document.getElementById("terminalScreen");
      try {
        const res = await fetch("/logs", { headers: authHeaders() });
        if (res.ok) {
          scr.textContent = await res.text();
          scr.scrollTop = scr.scrollHeight;
        }
      } catch (e) { scr.textContent = "LOG STREAM CONNECTION FAILED"; }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    window.addEventListener("DOMContentLoaded", () => {
      checkAuth();
    });
  </script>
</body>
</html>
"""


class WebDashboard:
    """Tactical operator console for 303 KYOMI with 6 integrated telemetry modules."""

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
                "bot_ready": self.bot.is_ready(),
                "guilds": len(self.bot.guilds),
                "retry_count": getattr(bot_module, "retry_count", 0),
                "last_bot_error": getattr(bot_module, "last_bot_error", "none"),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        )

    async def handle_logs(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.Response(text="unauthorized", status=401)

        log_candidates = [
            "bot.log",
            "data/bot.log",
            "app.log",
            "/home/container/bot.log",
        ]
        log_content = ""
        for path in log_candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        log_content = "".join(lines[-150:])
                        break
                except Exception:
                    pass

        if not log_content:
            log_content = (
                f"[SYSTEM STATUS: ONLINE]\n"
                f"Bot User: {self.bot.user}\n"
                f"Gateway WS Ping: {round(self.bot.latency * 1000, 1)}ms\n"
                f"Guilds Attached: {len(self.bot.guilds)}\n"
                f"Database Engine: SQLite (moderation.db)\n"
                f"No persistent logfile on disk yet. Active gateway sessions operational."
            )

        return web.Response(text=log_content, content_type="text/plain")

    async def handle_vitals(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)

        ping = round(self.bot.latency * 1000, 1) if self.bot.latency else 0
        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = getattr(self.bot, "start_time", now)
        diff = now - start_time
        days = diff.days
        hours, rem = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m {seconds}s"

        total_members = sum(g.member_count or 0 for g in self.bot.guilds)
        db_path = getattr(self.db, "db_path", "data/moderation.db")
        db_size_kb = 0
        if os.path.exists(db_path):
            db_size_kb = round(os.path.getsize(db_path) / 1024, 1)

        return web.json_response({
            "ping_ms": ping,
            "uptime": uptime_str,
            "cached_members": total_members,
            "db_size_kb": db_size_kb,
        })

    async def handle_guilds(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guilds = [
            {"id": str(g.id), "name": g.name, "member_count": g.member_count}
            for g in self.bot.guilds
        ]
        return web.json_response({"guilds": guilds})

    async def handle_guild_data(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        settings = await self.db.get_guild_settings(guild_id)
        words = await self.db.get_bad_words(guild_id)
        cases = await self.db.get_recent_mod_cases(guild_id, limit=5)
        return web.json_response({
            "settings": settings,
            "words": words,
            "cases": cases,
        })

    async def handle_update_setting(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        data = await request.json()
        key = data.get("key")
        val = data.get("value")
        await self.db.update_guild_setting(guild_id, key, val)
        return web.json_response({"status": "ok", "key": key, "value": val})

    async def handle_words(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        data = await request.json()
        action = data.get("action")
        word = data.get("word")
        if action == "add" and word:
            await self.db.add_bad_word(guild_id, word)
        elif action == "remove" and word:
            await self.db.remove_bad_word(guild_id, word)
        words = await self.db.get_bad_words(guild_id)
        return web.json_response({"status": "ok", "words": words})

    # --- 1. TICKETS ---
    async def handle_get_tickets(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(guild_id)
        raw_tickets = await self.db.get_tickets_for_guild(guild_id, limit=40)
        results = []
        for t in raw_tickets:
            ch = guild.get_channel(t["channel_id"]) if guild else None
            owner = guild.get_member(t["owner_id"]) if guild else None
            results.append({
                "id": t["id"],
                "channel_id": t["channel_id"],
                "channel_name": ch.name if ch else f"del-{t['channel_id']}",
                "owner_id": t["owner_id"],
                "owner_name": owner.name if owner else f"user_{t['owner_id']}",
                "category": t["category"],
                "status": t.get("status", "open"),
                "created_at": t.get("created_at"),
            })
        return web.json_response(results)

    async def handle_close_ticket(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        data = await request.json()
        channel_id = int(data.get("channel_id", 0))
        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id) if guild else None

        tickets_cog = self.bot.get_cog("Tickets")
        if channel and tickets_cog:
            from cogs.tickets import execute_close_sequence
            asyncio.create_task(execute_close_sequence(self.bot, channel, self.bot.user, None))
            return web.json_response({"status": "closing"})
        else:
            await self.db.close_ticket_record(channel_id)
            return web.json_response({"status": "closed_db_only"})

    # --- 2. DOSSIER ---
    async def handle_dossier(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        query = request.query.get("query", "").strip()
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return web.json_response({"error": "guild not found"}, status=404)

        target: discord.Member | None = None
        if query.isdigit():
            target = guild.get_member(int(query))
        if not target:
            target = discord.utils.find(
                lambda m: m.name.lower() == query.lower() or query.lower() in m.display_name.lower(),
                guild.members
            )

        if not target:
            return web.json_response({"error": "member not found in cache"}, status=404)

        warns = await self.db.get_warnings(guild_id, target.id)
        notes = await self.db.get_staff_notes(guild_id, target.id)

        # Standing logic
        days_on_discord = (datetime.datetime.now(datetime.timezone.utc) - target.created_at).days
        warn_count = len(warns)
        if warn_count >= 3:
            standing = "flagged"
        elif warn_count > 0:
            standing = "watched"
        elif days_on_discord > 365:
            standing = "trusted"
        else:
            standing = "clean"

        return web.json_response({
            "user_id": target.id,
            "name": target.name,
            "display_name": target.display_name,
            "avatar_url": target.display_avatar.url,
            "joined_at": target.joined_at.strftime("%Y-%m-%d %H:%M") if target.joined_at else "unknown",
            "created_at": target.created_at.strftime("%Y-%m-%d %H:%M"),
            "standing": standing,
            "strikes": warn_count,
            "notes": notes,
        })

    async def handle_dossier_note(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        data = await request.json()
        target_id = int(data.get("user_id"))
        note_text = str(data.get("note", "")).strip()
        if not note_text:
            return web.json_response({"error": "empty note"}, status=400)

        author_id = self.bot.user.id if self.bot.user else 0
        await self.db.add_staff_note(guild_id, target_id, author_id, f"[WEB OPERATOR] {note_text}")
        return web.json_response({"status": "recorded"})

    # --- 3. VANITY TRACKER ---
    async def handle_get_vanity(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(guild_id)
        settings = await self.db.get_guild_settings(guild_id)
        supporters_raw = await self.db.get_vanity_supporters(guild_id)

        role_id = settings.get("vanity_role_id")
        role = guild.get_role(role_id) if (guild and role_id) else None

        supporters = []
        for s in supporters_raw:
            m = guild.get_member(s["user_id"]) if guild else None
            supporters.append({
                "user_id": s["user_id"],
                "name": m.name if m else f"user_{s['user_id']}",
                "status_text": s.get("status_text") or "",
                "detected_at": s.get("detected_at") or 0,
            })

        return web.json_response({
            "enabled": bool(settings.get("vanity_enabled")),
            "phrase": settings.get("vanity_phrase") or ".gg/303",
            "role_id": role_id,
            "role_name": role.name if role else None,
            "channel_id": settings.get("vanity_channel_id"),
            "count": len(supporters),
            "supporters": supporters,
        })

    async def handle_vanity_scan(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return web.json_response({"error": "guild not found"}, status=404)
        vanity_cog = self.bot.get_cog("Vanity")
        if not vanity_cog:
            return web.json_response({"error": "vanity cog not active"}, status=500)

        settings = await self.db.get_guild_settings(guild_id)
        awarded = 0
        revoked = 0
        total = 0
        for m in guild.members:
            if m.bot:
                continue
            total += 1
            res = await vanity_cog._process_member_vanity(guild, m, settings=settings)
            if res is True:
                awarded += 1
            elif res is False:
                revoked += 1

        return web.json_response({
            "status": "ok",
            "scanned": total,
            "awarded": awarded,
            "revoked": revoked,
        })

    # --- 4. SNAPSHOTS ---
    async def handle_get_snapshots(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        raw = await self.db.get_snapshots(guild_id)
        results = []
        for s in raw:
            meta = json.loads(s.get("metadata_json", "{}"))
            results.append({
                "id": s["id"],
                "label": s["label"],
                "roles_count": meta.get("roles_count", 0),
                "channels_count": meta.get("channels_count", 0),
                "categories_count": meta.get("categories_count", 0),
                "created_at": s.get("created_at"),
            })
        return web.json_response(results)

    async def handle_create_snapshot(self, request: web.Request) -> web.Response:
        if not self._authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        guild_id = int(request.match_info["guild_id"])
        data = await request.json()
        label = str(data.get("label", "manual-web")).strip() or "manual-web"
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return web.json_response({"error": "guild not found"}, status=404)

        from cogs.snapshot import serialize_guild_structure
        roles_json, channels_json, metadata_json = serialize_guild_structure(guild)
        author_id = self.bot.user.id if self.bot.user else 0
        snap_id = await self.db.create_snapshot(
            guild_id=guild.id,
            creator_id=author_id,
            label=label,
            roles_json=roles_json,
            channels_json=channels_json,
            metadata_json=metadata_json,
        )
        return web.json_response({"status": "created", "snapshot_id": snap_id})

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

    # --- 5. BUMP MODULE ---
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

        # 6 Modules Routes
        app.router.add_get("/api/guild/{guild_id}/tickets", self.handle_get_tickets)
        app.router.add_post("/api/guild/{guild_id}/ticket/close", self.handle_close_ticket)
        app.router.add_get("/api/guild/{guild_id}/dossier", self.handle_dossier)
        app.router.add_post("/api/guild/{guild_id}/dossier/note", self.handle_dossier_note)
        app.router.add_get("/api/guild/{guild_id}/vanity", self.handle_get_vanity)
        app.router.add_post("/api/guild/{guild_id}/vanity/scan", self.handle_vanity_scan)
        app.router.add_get("/api/guild/{guild_id}/snapshots", self.handle_get_snapshots)
        app.router.add_post("/api/guild/{guild_id}/snapshots/create", self.handle_create_snapshot)
        app.router.add_get("/api/snapshots/{snapshot_id}/download", self.handle_download_snapshot)
        app.router.add_get("/api/guild/{guild_id}/bump", self.handle_bump_data)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await site.start()
        logger.info("303 KYOMI Operator Console live on port %s", self.port)

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()
