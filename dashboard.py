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
  <title>303 kyomi  ✦  control panel</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #09090b;
      --surface: #0f0f13;
      --surface-hover: #14141a;
      --surface-elevated: #131318;
      --border: #1a1a23;
      --border-subtle: #242430;
      --text: #e6e6ef;
      --text-muted: #6e6f7e;
      --text-dim: #9b9ca8;
      --accent: #8a1c27;
      --accent-hover: #a32230;
      --accent-muted: rgba(138, 28, 39, 0.16);
      --mint: #5bb98c;
      --mint-muted: rgba(91, 185, 140, 0.12);
      --amber: #cca05c;
      --amber-muted: rgba(204, 160, 92, 0.12);
      --font: 'Inter', -apple-system, sans-serif;
      --mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font);
      min-height: 100vh;
      padding: 24px 22px 64px;
      letter-spacing: -0.012em;
      font-size: 13px;
      line-height: 1.5;
    }

    .container { max-width: 1120px; margin: 0 auto; }

    /* Minimalist Auth Overlay */
    #authOverlay {
      position: fixed; inset: 0;
      background: rgba(9, 9, 11, 0.95);
      backdrop-filter: blur(10px);
      display: flex; align-items: center; justify-content: center; z-index: 9999;
    }
    .auth-box {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 32px 28px;
      width: 100%; max-width: 360px;
      text-align: center;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.85);
    }
    .auth-title {
      font-size: 14px;
      font-weight: 500;
      color: #fff;
      margin-bottom: 4px;
      letter-spacing: 0.02em;
    }
    .auth-desc {
      font-size: 11.5px;
      color: var(--text-muted);
      margin-bottom: 18px;
      font-family: var(--mono);
    }

    /* Dark Aesthetic Header */
    header.sanctuary-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 18px; flex-wrap: wrap; gap: 14px;
    }
    .brand-mark { display: flex; align-items: center; gap: 12px; }
    .brand-sigil {
      font-family: var(--mono);
      font-size: 13px;
      font-weight: 600;
      color: #fff;
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 8px;
      letter-spacing: 0.04em;
    }
    .brand-name {
      font-size: 15px;
      font-weight: 600;
      color: #fff;
      letter-spacing: -0.02em;
    }
    .brand-sub {
      font-size: 11.5px;
      color: var(--text-muted);
    }

    .header-controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .status-pill {
      font-size: 11.5px;
      font-family: var(--mono);
      padding: 6px 12px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      display: inline-flex; align-items: center; gap: 7px;
      color: var(--text-dim);
    }
    .status-pill.online {
      color: var(--mint);
      border-color: rgba(91, 185, 140, 0.25);
      background: var(--mint-muted);
    }
    .status-dot {
      width: 6px; height: 6px; border-radius: 50%; background: currentColor;
    }

    select.guild-selector {
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 7px 12px;
      font-size: 12px;
      font-family: var(--mono);
      cursor: pointer;
      outline: none;
      transition: border-color 0.15s;
    }
    select.guild-selector:focus { border-color: var(--border-subtle); }

    /* Vitals Row */
    .vitals-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 20px;
    }
    @media (max-width: 860px) { .vitals-bar { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 480px) { .vitals-bar { grid-template-columns: 1fr; } }

    .vital-item {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
    }
    .vital-title {
      font-size: 11px;
      color: var(--text-muted);
      margin-bottom: 4px;
      display: flex; align-items: center; justify-content: space-between;
    }
    .vital-value {
      font-size: 16px;
      font-weight: 600;
      font-family: var(--mono);
      color: #fff;
    }

    /* Tabs Navigation */
    .nav-tabs {
      display: flex; gap: 6px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 10px;
      margin-bottom: 22px;
      overflow-x: auto;
    }
    .tab-item {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      font-size: 12px;
      padding: 7px 14px;
      border-radius: 6px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
      display: flex; align-items: center; gap: 6px;
    }
    .tab-item:hover {
      color: var(--text);
      background: var(--surface);
    }
    .tab-item.active {
      color: #fff;
      background: var(--surface);
      border-color: var(--border);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }

    /* Panes */
    .pane-content { display: none; }
    .pane-content.active { display: block; }

    /* Content Cards */
    .dark-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 16px;
    }
    .card-title-bar {
      display: flex; align-items: center; justify-content: space-between;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
      margin-bottom: 16px;
    }
    .card-title {
      font-size: 13px;
      font-weight: 600;
      color: #fff;
      display: flex; align-items: center; gap: 8px;
    }

    .duo-layout {
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 16px;
    }
    @media (max-width: 860px) { .duo-layout { grid-template-columns: 1fr; } }

    /* Setting Rows */
    .toggle-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 11px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.02);
    }
    .toggle-row:last-child { border-bottom: none; }
    .toggle-name { font-size: 13px; font-weight: 500; color: #fff; margin-bottom: 2px; }
    .toggle-sub { font-size: 11.5px; color: var(--text-muted); }

    /* Dark Aesthetic Smooth Toggle Switch */
    .smooth-switch {
      position: relative;
      display: inline-block;
      width: 36px;
      height: 20px;
      flex-shrink: 0;
    }
    .smooth-switch input { opacity: 0; width: 0; height: 0; }
    .switch-track {
      position: absolute; cursor: pointer; inset: 0;
      background-color: #1a1a24;
      border: 1px solid var(--border);
      border-radius: 20px;
      transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .switch-track:before {
      position: absolute; content: "";
      height: 12px; width: 12px;
      left: 3px; bottom: 3px;
      background-color: #8c8d9e;
      border-radius: 50%;
      transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    input:checked + .switch-track {
      background-color: var(--accent);
      border-color: var(--accent);
    }
    input:checked + .switch-track:before {
      transform: translateX(16px);
      background-color: #fff;
    }

    /* Inputs & Buttons */
    input[type="text"], input[type="password"], input[type="number"] {
      background: #0b0b0e;
      border: 1px solid var(--border);
      border-radius: 6px;
      color: #fff;
      padding: 8px 12px;
      font-size: 12px;
      font-family: var(--mono);
      outline: none;
      transition: border-color 0.15s;
    }
    input[type="text"]:focus, input[type="password"]:focus {
      border-color: var(--border-subtle);
    }

    .btn-dark {
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text);
      padding: 7px 13px;
      font-size: 12px;
      cursor: pointer;
      display: inline-flex; align-items: center; gap: 6px;
      transition: all 0.15s;
    }
    .btn-dark:hover {
      background: var(--surface-hover);
      border-color: var(--border-subtle);
      color: #fff;
    }
    .btn-dark.crimson {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }
    .btn-dark.crimson:hover {
      background: var(--accent-hover);
      border-color: var(--accent-hover);
    }

    /* Minimalist Tables */
    table.dark-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    table.dark-table th {
      text-align: left;
      font-size: 11px;
      color: var(--text-muted);
      padding: 9px 10px;
      border-bottom: 1px solid var(--border);
      font-weight: 500;
    }
    table.dark-table td {
      padding: 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.02);
      color: var(--text-dim);
      font-family: var(--mono);
    }
    table.dark-table tr:hover td {
      background: rgba(255, 255, 255, 0.015);
      color: #fff;
    }

    /* Minimal Monochrome Badges */
    .badge {
      font-size: 11px;
      font-family: var(--mono);
      padding: 3px 8px;
      border-radius: 4px;
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      color: var(--text-dim);
      display: inline-block;
    }
    .badge.green {
      color: var(--mint);
      border-color: rgba(91, 185, 140, 0.3);
      background: var(--mint-muted);
    }
    .badge.amber {
      color: var(--amber);
      border-color: rgba(204, 160, 92, 0.3);
      background: var(--amber-muted);
    }
    .badge.red {
      color: #ff7886;
      border-color: rgba(138, 28, 39, 0.4);
      background: var(--accent-muted);
    }

    /* Words Chip Cloud */
    .word-cloud { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
    .word-pill {
      background: #0b0b0e;
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 4px 9px;
      font-size: 11.5px;
      font-family: var(--mono);
      display: inline-flex; align-items: center; gap: 6px;
    }
    .word-x { cursor: pointer; color: var(--text-muted); }
    .word-x:hover { color: #ff6070; }

    /* Feed Terminal Box */
    .feed-terminal {
      background: #060608;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 14px;
      font-family: var(--mono);
      font-size: 11.5px;
      line-height: 1.6;
      color: #a0a1b0;
      max-height: 380px;
      overflow-y: auto;
      white-space: pre-wrap;
    }

    /* Toast Notification */
    #actionBanner {
      position: fixed; bottom: 20px; right: 20px;
      background: #111116; border: 1px solid var(--border-subtle);
      padding: 10px 16px; border-radius: 6px;
      font-size: 12px; color: #fff; z-index: 999; display: none;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8);
    }
  </style>
</head>
<body>

  <!-- Passkey Screen -->
  <div id="authOverlay" style="display: none;">
    <div class="auth-box">
      <div class="auth-title">✦ 303 kyomi</div>
      <div class="auth-desc">enter passkey to unlock control panel</div>
      <input type="password" id="passkeyInput" placeholder="passkey..." style="width: 100%; margin-bottom: 12px;" onkeydown="if(event.key==='Enter') verifyPasskey()">
      <button class="btn-dark crimson" style="width: 100%; justify-content: center;" onclick="verifyPasskey()">unlock</button>
    </div>
  </div>

  <div id="actionBanner"></div>

  <div class="container">
    <!-- Header -->
    <header class="sanctuary-header">
      <div class="brand-mark">
        <div class="brand-sigil">303</div>
        <div>
          <div class="brand-name">kyomi</div>
          <div class="brand-sub">security, moderation & archival</div>
        </div>
      </div>
      <div class="header-controls">
        <div class="status-pill online" id="statusPill">
          <div class="status-dot"></div>
          <span id="statusText">active</span>
        </div>
        <select class="guild-selector" id="guildSelect" onchange="loadGuildData()">
          <option value="">loading...</option>
        </select>
        <button class="btn-dark" style="padding: 6px 11px; font-size: 11.5px;" onclick="lockDashboard()" title="lock session">× lock</button>
      </div>
    </header>

    <!-- Vitals Row -->
    <div class="vitals-bar">
      <div class="vital-item">
        <div class="vital-title"><span>gateway ping</span><span>◈</span></div>
        <div class="vital-value" id="vital_ping">-- ms</div>
      </div>
      <div class="vital-item">
        <div class="vital-title"><span>uptime</span><span>◇</span></div>
        <div class="vital-value" id="vital_uptime">--</div>
      </div>
      <div class="vital-item">
        <div class="vital-title"><span>cached members</span><span>✧</span></div>
        <div class="vital-value" id="vital_members">--</div>
      </div>
      <div class="vital-item">
        <div class="vital-title"><span>database footprint</span><span>▸</span></div>
        <div class="vital-value" id="vital_dbsize">-- KB</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <nav class="nav-tabs">
      <button class="tab-item active" onclick="switchPane('automod', event)">✦ automod</button>
      <button class="tab-item" onclick="switchPane('tickets', event)">◈ tickets</button>
      <button class="tab-item" onclick="switchPane('dossier', event)">◇ dossier</button>
      <button class="tab-item" onclick="switchPane('vanity', event)">✧ vanity tracker</button>
      <button class="tab-item" onclick="switchPane('snapshots', event)">▸ snapshots</button>
      <button class="tab-item" onclick="switchPane('bumping', event)">○ disboard</button>
      <button class="tab-item" onclick="switchPane('system', event)">† system feed</button>
    </nav>

    <!-- PANE 1: AUTOMOD -->
    <section id="pane-automod" class="pane-content active">
      <div class="duo-layout">
        <div class="dark-card">
          <div class="card-title-bar">
            <div class="card-title">✦ security & automod rules</div>
            <span class="badge green">armed</span>
          </div>

          <div class="toggle-row">
            <div>
              <div class="toggle-name">master automod</div>
              <div class="toggle-sub">primary enforcement filter for all incoming messages</div>
            </div>
            <label class="smooth-switch">
              <input type="checkbox" id="sw_automod" onchange="toggleSetting('automod_enabled', this.checked)">
              <span class="switch-track"></span>
            </label>
          </div>

          <div class="toggle-row">
            <div>
              <div class="toggle-name">anti-spam filter</div>
              <div class="toggle-sub">detects velocity spam (5 messages in 5 seconds)</div>
            </div>
            <label class="smooth-switch">
              <input type="checkbox" id="sw_antispam" onchange="toggleSetting('anti_spam_enabled', this.checked)">
              <span class="switch-track"></span>
            </label>
          </div>

          <div class="toggle-row">
            <div>
              <div class="toggle-name">anti-raid ingress shield</div>
              <div class="toggle-sub">blocks mass joins and unverified burner accounts</div>
            </div>
            <label class="smooth-switch">
              <input type="checkbox" id="sw_antiraid" onchange="toggleSetting('antiraid_enabled', this.checked)">
              <span class="switch-track"></span>
            </label>
          </div>

          <div class="toggle-row">
            <div>
              <div class="toggle-name">anti-ghostping guard</div>
              <div class="toggle-sub">detects and logs deleted messages containing mentions</div>
            </div>
            <label class="smooth-switch">
              <input type="checkbox" id="sw_ghostping" onchange="toggleSetting('ghostping_enabled', this.checked)">
              <span class="switch-track"></span>
            </label>
          </div>

          <div class="toggle-row">
            <div>
              <div class="toggle-name">anti-invite quarantine</div>
              <div class="toggle-sub">auto-deletes unauthorized discord server invites</div>
            </div>
            <label class="smooth-switch">
              <input type="checkbox" id="sw_invites" onchange="toggleSetting('block_invites', this.checked)">
              <span class="switch-track"></span>
            </label>
          </div>

          <div class="toggle-row">
            <div>
              <div class="toggle-name">anti-link filter</div>
              <div class="toggle-sub">blocks unauthorized external URLs from chat</div>
            </div>
            <label class="smooth-switch">
              <input type="checkbox" id="sw_links" onchange="toggleSetting('block_links', this.checked)">
              <span class="switch-track"></span>
            </label>
          </div>
        </div>

        <div>
          <!-- Word Filter Card -->
          <div class="dark-card">
            <div class="card-title-bar">
              <div class="card-title">◈ filtered words</div>
            </div>
            <div style="display: flex; gap: 6px; margin-bottom: 12px;">
              <input type="text" id="newWordInput" placeholder="add word or pattern..." style="flex: 1;">
              <button class="btn-dark crimson" onclick="addFilterWord()">add</button>
            </div>
            <div class="word-cloud" id="wordMatrix">
              <span class="badge">no filtered words</span>
            </div>
          </div>

          <!-- Mod Cases Card -->
          <div class="dark-card">
            <div class="card-title-bar">
              <div class="card-title">◇ recent infractions</div>
            </div>
            <table class="dark-table">
              <thead>
                <tr>
                  <th>case</th>
                  <th>action</th>
                  <th>target</th>
                  <th>reason</th>
                </tr>
              </thead>
              <tbody id="modCasesBody">
                <tr><td colspan="4" style="color: var(--text-muted); text-align: center;">no infractions recorded</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- PANE 2: TICKETS -->
    <section id="pane-tickets" class="pane-content">
      <div class="dark-card">
        <div class="card-title-bar">
          <div class="card-title">◈ ticket rooms & archives</div>
          <button class="btn-dark" onclick="loadTickets()">refresh</button>
        </div>
        <table class="dark-table">
          <thead>
            <tr>
              <th>id</th>
              <th>channel</th>
              <th>opener</th>
              <th>topic</th>
              <th>status</th>
              <th>created</th>
              <th>action</th>
            </tr>
          </thead>
          <tbody id="ticketsBody">
            <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">fetching ticket rooms...</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- PANE 3: DOSSIER -->
    <section id="pane-dossier" class="pane-content">
      <div class="dark-card">
        <div class="card-title-bar">
          <div class="card-title">◇ member dossier search</div>
        </div>
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <input type="text" id="dossierQuery" placeholder="user id or username..." style="flex: 1;">
          <button class="btn-dark crimson" onclick="searchDossier()">search</button>
        </div>

        <div id="dossierResult" style="display: none;">
          <div class="duo-layout">
            <div class="dark-card" style="background: #0b0b0f; margin-bottom: 0;">
              <div style="display: flex; gap: 14px; align-items: center; margin-bottom: 14px;">
                <img id="dos_avatar" src="" style="width: 44px; height: 44px; border: 1px solid var(--border); border-radius: 6px;">
                <div>
                  <div id="dos_name" style="font-size: 14px; font-weight: 600; color: #fff;">--</div>
                  <div id="dos_id" style="font-size: 11px; color: var(--text-muted); font-family: var(--mono);">--</div>
                </div>
              </div>
              <div class="toggle-row">
                <span class="toggle-sub">standing</span>
                <span id="dos_standing" class="badge">--</span>
              </div>
              <div class="toggle-row">
                <span class="toggle-sub">joined</span>
                <span id="dos_joined" style="font-family: var(--mono); color: #fff;">--</span>
              </div>
              <div class="toggle-row">
                <span class="toggle-sub">account created</span>
                <span id="dos_created" style="font-family: var(--mono); color: #fff;">--</span>
              </div>
              <div class="toggle-row">
                <span class="toggle-sub">warnings (strikes)</span>
                <span id="dos_strikes" style="font-family: var(--mono); color: #fff; font-weight: 600;">0</span>
              </div>
            </div>

            <div class="dark-card" style="background: #0b0b0f; margin-bottom: 0;">
              <div class="card-title" style="margin-bottom: 10px;">staff observations</div>
              <div style="display: flex; gap: 6px; margin-bottom: 12px;">
                <input type="text" id="dos_note_input" placeholder="add note..." style="flex: 1;">
                <button class="btn-dark crimson" onclick="addDossierNote()">save</button>
              </div>
              <div id="dos_notes_list" style="max-height: 180px; overflow-y: auto;">
                <div style="color: var(--text-muted); font-size: 11.5px;">no notes on record</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- PANE 4: VANITY TRACKER -->
    <section id="pane-vanity" class="pane-content">
      <div class="duo-layout">
        <div class="dark-card">
          <div class="card-title-bar">
            <div class="card-title">✧ vanity status tracker</div>
            <span class="badge" id="vnt_status_chip">checking</span>
          </div>

          <div class="toggle-row">
            <div>
              <div class="toggle-name">tracker enabled</div>
              <div class="toggle-sub">automatically awards supporter role when detected</div>
            </div>
            <label class="smooth-switch">
              <input type="checkbox" id="sw_vanity" onchange="toggleSetting('vanity_enabled', this.checked)">
              <span class="switch-track"></span>
            </label>
          </div>

          <div style="margin-top: 14px;">
            <div class="toggle-sub" style="margin-bottom: 4px;">target vanity phrase</div>
            <div style="display: flex; gap: 6px;">
              <input type="text" id="vnt_phrase_input" placeholder="e.g. .gg/303 or /303" style="flex: 1;">
              <button class="btn-dark" onclick="saveVanityPhrase()">save phrase</button>
            </div>
          </div>

          <div style="margin-top: 14px;">
            <div class="toggle-sub" style="margin-bottom: 4px;">supporter role id</div>
            <div style="display: flex; gap: 6px;">
              <input type="text" id="vnt_role_input" placeholder="role id..." style="flex: 1;">
              <button class="btn-dark" onclick="saveVanityRole()">link role</button>
            </div>
          </div>

          <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border);">
            <button class="btn-dark crimson" style="width: 100%; justify-content: center;" onclick="triggerVanityScan()">
              † scan & sync members now
            </button>
          </div>
        </div>

        <div class="dark-card">
          <div class="card-title-bar">
            <div class="card-title">✧ active supporters</div>
            <span class="badge green" id="vnt_count_chip">0 supporters</span>
          </div>

          <table class="dark-table">
            <thead>
              <tr>
                <th>member</th>
                <th>custom status</th>
                <th>detected</th>
              </tr>
            </thead>
            <tbody id="vnt_supporters_body">
              <tr><td colspan="3" style="text-align: center; color: var(--text-muted);">no supporters found</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- PANE 5: SNAPSHOTS -->
    <section id="pane-snapshots" class="pane-content">
      <div class="dark-card">
        <div class="card-title-bar">
          <div class="card-title">▸ server snapshots & backups</div>
          <button class="btn-dark crimson" onclick="createSnapshotWeb()">+ new snapshot</button>
        </div>
        <table class="dark-table">
          <thead>
            <tr>
              <th>id</th>
              <th>label</th>
              <th>roles</th>
              <th>channels</th>
              <th>categories</th>
              <th>date</th>
              <th>export</th>
            </tr>
          </thead>
          <tbody id="snapshotsBody">
            <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">loading snapshots...</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- PANE 6: DISBOARD -->
    <section id="pane-bumping" class="pane-content">
      <div class="duo-layout">
        <div class="dark-card">
          <div class="card-title-bar">
            <div class="card-title">○ bump countdown</div>
          </div>
          <div style="text-align: center; padding: 24px 10px;">
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px;">next disboard bump</div>
            <div id="bumpCountdown" style="font-family: var(--mono); font-size: 34px; font-weight: 600; color: #fff;">00:00:00</div>
            <div id="bumpStatusNotice" style="font-size: 11.5px; color: var(--mint); margin-top: 6px;">ready to bump</div>
          </div>
        </div>

        <div class="dark-card">
          <div class="card-title-bar">
            <div class="card-title">○ bump leaderboard</div>
          </div>
          <table class="dark-table">
            <thead>
              <tr>
                <th>rank</th>
                <th>member</th>
                <th>bumps</th>
              </tr>
            </thead>
            <tbody id="bumpLeaderboardBody">
              <tr><td colspan="3" style="text-align: center; color: var(--text-muted);">no bumps logged</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- PANE 7: CONSOLE LOGS -->
    <section id="pane-system" class="pane-content">
      <div class="dark-card">
        <div class="card-title-bar">
          <div class="card-title">† system terminal feed</div>
          <button class="btn-dark" onclick="fetchLogs()">refresh feed</button>
        </div>
        <div class="feed-terminal" id="terminalScreen">connecting to feed...</div>
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
      b.style.borderColor = isError ? "var(--accent)" : "var(--border-subtle)";
      b.style.display = "block";
      setTimeout(() => { b.style.display = "none"; }, 3000);
    }

    function switchPane(paneId, ev) {
      document.querySelectorAll(".pane-content").forEach(el => el.classList.remove("active"));
      document.querySelectorAll(".tab-item").forEach(el => el.classList.remove("active"));
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
      if (!val) return;
      passkey = val;
      localStorage.setItem("kyomi_passkey", val);
      try {
        const res = await fetch("/api/guilds", { headers: authHeaders() });
        if (res.status === 401) {
          document.getElementById("authOverlay").style.display = "flex";
          showBanner("invalid passkey", true);
        } else {
          document.getElementById("authOverlay").style.display = "none";
          showBanner("access granted");
          const data = await res.json();
          renderGuildSelect(data.guilds || []);
          startTelemetryLoop();
        }
      } catch (e) {
        showBanner("connection error", true);
      }
    }

    function lockDashboard() {
      localStorage.removeItem("kyomi_passkey");
      passkey = "";
      document.getElementById("passkeyInput").value = "";
      document.getElementById("authOverlay").style.display = "flex";
      showBanner("dashboard locked");
    }

    function renderGuildSelect(guilds) {
      const sel = document.getElementById("guildSelect");
      sel.innerHTML = "";
      if (!guilds || guilds.length === 0) {
        sel.innerHTML = '<option value="">no servers connected</option>';
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

        document.getElementById("sw_automod").checked = s.automod_enabled !== 0;
        document.getElementById("sw_antispam").checked = s.anti_spam_enabled !== 0;
        document.getElementById("sw_antiraid").checked = s.antiraid_enabled !== 0;
        document.getElementById("sw_ghostping").checked = s.ghostping_enabled !== 0;
        document.getElementById("sw_invites").checked = s.block_invites !== 0;
        document.getElementById("sw_links").checked = s.block_links !== 0;
        document.getElementById("sw_vanity").checked = s.vanity_enabled === 1;

        renderWords(data.words || []);
        renderModCases(data.cases || []);
      } catch (e) {
        console.error(e);
      }
    }

    async function toggleSetting(settingKey, isChecked) {
      const nextVal = isChecked ? 1 : 0;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/setting`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ key: settingKey, value: nextVal })
        });
        if (res.ok) showBanner(`updated ${settingKey}`);
      } catch (e) {
        showBanner("failed to save setting", true);
      }
    }

    function renderWords(words) {
      cachedWords = words;
      const matrix = document.getElementById("wordMatrix");
      matrix.innerHTML = "";
      if (!words || words.length === 0) {
        matrix.innerHTML = '<span class="badge">no filtered words</span>';
        return;
      }
      words.forEach(w => {
        const unit = document.createElement("div");
        unit.className = "word-pill";
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
          showBanner(`added filtered pattern: ${word}`);
          loadGuildData();
        }
      } catch (e) { showBanner("failed to add word", true); }
    }

    async function deleteWord(word) {
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/words`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ action: "remove", word })
        });
        if (res.ok) {
          showBanner(`removed word: ${word}`);
          loadGuildData();
        }
      } catch (e) { showBanner("failed to remove word", true); }
    }

    function renderModCases(cases) {
      const tbody = document.getElementById("modCasesBody");
      tbody.innerHTML = "";
      if (!cases || cases.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="color: var(--text-muted); text-align: center;">no recent infractions</td></tr>';
        return;
      }
      cases.forEach(c => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>#${c.id}</td>
          <td><span class="badge red">${c.action.toLowerCase()}</span></td>
          <td>${c.target_id}</td>
          <td>${escapeHtml(c.reason || 'none')}</td>
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
          tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">no ticket rooms found</td></tr>';
          return;
        }
        list.forEach(t => {
          const tr = document.createElement("tr");
          const stateColor = t.status === "open" ? "green" : (t.status === "archived" ? "amber" : "");
          tr.innerHTML = `
            <td>#${t.id}</td>
            <td><code>${escapeHtml(t.channel_name || t.channel_id)}</code></td>
            <td>${escapeHtml(t.owner_name || t.owner_id)}</td>
            <td><span class="badge">${escapeHtml(t.category)}</span></td>
            <td><span class="badge ${stateColor}">${t.status.toLowerCase()}</span></td>
            <td>${t.created_at ? t.created_at.slice(0, 16) : '--'}</td>
            <td>
              ${t.status !== 'closed' ? `<button class="btn-dark" style="padding: 3px 8px;" onclick="closeTicketRemote(${t.channel_id})">close</button>` : '--'}
            </td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">tickets feed offline</td></tr>';
      }
    }

    async function closeTicketRemote(channelId) {
      if (!confirm("close ticket channel and export transcript?")) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/ticket/close`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ channel_id: channelId })
        });
        if (res.ok) {
          showBanner("ticket closing sequence started");
          loadTickets();
        }
      } catch (e) { showBanner("failed to close ticket", true); }
    }

    // --- DOSSIER ---
    let currentDossierUserId = null;
    async function searchDossier() {
      const q = document.getElementById("dossierQuery").value.trim();
      if (!q || !currentGuildId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/dossier?query=${encodeURIComponent(q)}`, { headers: authHeaders() });
        if (!res.ok) return showBanner("member not found in cache", true);
        const data = await res.json();
        currentDossierUserId = data.user_id;

        document.getElementById("dos_name").textContent = data.name;
        document.getElementById("dos_id").textContent = `id: ${data.user_id}`;
        document.getElementById("dos_avatar").src = data.avatar_url || "https://cdn.discordapp.com/embed/avatars/0.png";
        document.getElementById("dos_standing").textContent = (data.standing || "clean").toLowerCase();
        document.getElementById("dos_standing").className = "badge " + (data.standing === "trusted" ? "green" : (data.standing === "flagged" ? "red" : "amber"));
        document.getElementById("dos_joined").textContent = data.joined_at || "--";
        document.getElementById("dos_created").textContent = data.created_at || "--";
        document.getElementById("dos_strikes").textContent = data.strikes || 0;

        renderDossierNotes(data.notes || []);
        document.getElementById("dossierResult").style.display = "block";
      } catch (e) { showBanner("dossier lookup failed", true); }
    }

    function renderDossierNotes(notes) {
      const container = document.getElementById("dos_notes_list");
      container.innerHTML = "";
      if (!notes || notes.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 11.5px;">no staff notes recorded</div>';
        return;
      }
      notes.forEach(n => {
        const item = document.createElement("div");
        item.style.padding = "6px 0";
        item.style.borderBottom = "1px solid rgba(255, 255, 255, 0.025)";
        item.innerHTML = `
          <div style="display: flex; justify-content: space-between; font-size: 10.5px; color: var(--text-muted); font-family: var(--mono);">
            <span>author: ${n.author_id}</span>
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
          showBanner("note saved");
          searchDossier();
        }
      } catch (e) { showBanner("failed to save note", true); }
    }

    // --- VANITY TRACKER ---
    async function loadVanity() {
      if (!currentGuildId) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/vanity`, { headers: authHeaders() });
        if (!res.ok) return;
        const v = await res.json();

        document.getElementById("sw_vanity").checked = v.enabled;
        const chip = document.getElementById("vnt_status_chip");
        chip.textContent = v.enabled ? "active" : "disabled";
        chip.className = "badge " + (v.enabled ? "green" : "");

        document.getElementById("vnt_phrase_input").value = v.phrase || ".gg/303";
        document.getElementById("vnt_role_input").value = v.role_id || "";
        document.getElementById("vnt_count_chip").textContent = `${v.count} supporters`;

        const tbody = document.getElementById("vnt_supporters_body");
        tbody.innerHTML = "";
        if (!v.supporters || v.supporters.length === 0) {
          tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">no supporters found</td></tr>';
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
        if (res.ok) showBanner(`vanity phrase saved: ${phrase}`);
      } catch (e) { showBanner("failed to save phrase", true); }
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
        if (res.ok) showBanner(`supporter role linked: ${roleId}`);
      } catch (e) { showBanner("failed to link role", true); }
    }

    async function triggerVanityScan() {
      showBanner("scanning members for vanity status...");
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/vanity/scan`, {
          method: "POST",
          headers: authHeaders()
        });
        if (res.ok) {
          const r = await res.json();
          showBanner(`scan complete: ${r.scanned} scanned, ${r.awarded} awarded, ${r.revoked} revoked`);
          loadVanity();
        } else {
          showBanner("scan failed", true);
        }
      } catch (e) { showBanner("failed to trigger scan", true); }
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
          tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">no snapshots created</td></tr>';
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
              <a href="/api/snapshots/${s.id}/download?key=${encodeURIComponent(passkey)}" class="btn-dark" style="padding: 3px 8px; text-decoration: none;">export json</a>
            </td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) { tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">snapshots unavailable</td></tr>'; }
    }

    async function createSnapshotWeb() {
      const label = prompt("enter snapshot label:", "backup");
      if (!label) return;
      try {
        const res = await fetch(`/api/guild/${currentGuildId}/snapshots/create`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ label })
        });
        if (res.ok) {
          showBanner("snapshot saved");
          loadSnapshots();
        }
      } catch (e) { showBanner("failed to create snapshot", true); }
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
            document.getElementById("bumpCountdown").textContent = "ready";
            document.getElementById("bumpCountdown").style.color = "var(--mint)";
            document.getElementById("bumpStatusNotice").textContent = "ready to bump";
          } else {
            const h = Math.floor(rem / 3600);
            const m = Math.floor((rem % 3600) / 60);
            const s = rem % 60;
            document.getElementById("bumpCountdown").textContent =
              `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
            document.getElementById("bumpCountdown").style.color = "#fff";
            document.getElementById("bumpStatusNotice").textContent = "cooldown active";
            rem--;
          }
        };
        clearInterval(bumpTimerInterval);
        renderTimer();
        bumpTimerInterval = setInterval(renderTimer, 1000);

        const tbody = document.getElementById("bumpLeaderboardBody");
        tbody.innerHTML = "";
        if (!d.leaderboard || d.leaderboard.length === 0) {
          tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">no bumps logged</td></tr>';
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
      } catch (e) { scr.textContent = "logs stream connection error"; }
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
    """Dark aesthetic web control panel for 303 KYOMI with 6 integrated modules."""

    def __init__(self, bot: discord.Client, db, port: int = 3030):
        self.bot = bot
        self.db = db
        # Automatically detects Wispbyte/Pterodactyl SERVER_PORT
        self.port = int(os.getenv("PORT", os.getenv("SERVER_PORT", port)))
        self.password = os.getenv("DASHBOARD_PASSWORD", "303kyomi").strip() or "303kyomi"
        self.runner: web.AppRunner | None = None

    def _authorized(self, request: web.Request) -> bool:
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
                f"[303 kyomi  ✦  active]\n"
                f"bot: {self.bot.user}\n"
                f"gateway ping: {round(self.bot.latency * 1000, 1)}ms\n"
                f"connected guilds: {len(self.bot.guilds)}\n"
                f"database: sqlite (moderation.db)\n"
                f"gateway session operational."
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
        await self.db.add_staff_note(guild_id, target_id, author_id, f"[operator] {note_text}")
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
        label = str(data.get("label", "web-backup")).strip() or "web-backup"
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
        logger.info("303 KYOMI Control Panel online on port %s", self.port)

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()
