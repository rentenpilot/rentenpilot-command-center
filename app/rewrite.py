import re
import os

app_dir = r"C:\AI\rentenpilot-command-center\app"
index_path = os.path.join(app_dir, "templates", "index.html")
style_path = os.path.join(app_dir, "static", "css", "style.css")

with open(index_path, "r", encoding="utf-8") as f:
    old_html = f.read()

# Extract the <script> part exactly as it is
script_match = re.search(r'(<script>.*?</script>)', old_html, re.DOTALL)
if script_match:
    js_content = script_match.group(1)
else:
    print("Could not find <script> in index.html")
    exit(1)

# Now we will rewrite the JS content to map to the new module IDs
new_overlay_data = """
    const overlayData = {
        'mod-research': {
            title: 'RESEARCH',
            html: '<div class="hud-data-row"><span class="hud-data-k">Status</span><span class="hud-data-v text-green">Aktiv</span></div><div class="hud-data-row"><span class="hud-data-k">Neue Themen</span><span class="hud-data-v">14</span></div><div class="hud-data-row"><span class="hud-data-k">Quellen heute</span><span class="hud-data-v">32</span></div><div class="hud-data-desc">Recherche und Analyse von Geschäftsfeldern und neuen Trends.</div>'
        },
        'mod-content': {
            title: 'CONTENT',
            html: '<div class="hud-data-row"><span class="hud-data-k">Status</span><span class="hud-data-v text-green">Aktiv</span></div><div class="hud-data-row"><span class="hud-data-k">Artikel Entwürfe</span><span class="hud-data-v">7</span></div><div class="hud-data-row"><span class="hud-data-k">Veröffentlicht heute</span><span class="hud-data-v">1</span></div><div class="hud-data-desc">Erstellung und Optimierung von Artikeln.</div>'
        },
        'mod-trading': {
            title: 'TRADING SIGNALS',
            html: '<div class="hud-data-row"><span class="hud-data-k">Status</span><span class="hud-data-v text-green">Aktiv</span></div><div class="hud-data-row"><span class="hud-data-k">Aktive Signale</span><span class="hud-data-v">2</span></div><div class="hud-data-row"><span class="hud-data-k">Trefferquote</span><span class="hud-data-v">71%</span></div><div class="hud-data-row"><span class="hud-data-k">Letztes Signal</span><span class="hud-data-v">LONG BTC/USD</span></div><button class="hud-action-btn">SIGNAL CENTER</button>'
        },
        'mod-publisher': {
            title: 'PUBLISHER',
            html: '<div class="hud-data-row"><span class="hud-data-k">Status</span><span class="hud-data-v text-green">Aktiv</span></div><div class="hud-data-row"><span class="hud-data-k">Geplant</span><span class="hud-data-v">5</span></div><div class="hud-data-desc">Automatische Veröffentlichung von Content.</div>'
        },
        'mod-social': {
            title: 'SOCIAL MEDIA',
            html: '<div class="hud-data-row"><span class="hud-data-k">Status</span><span class="hud-data-v text-green">Aktiv</span></div><div class="hud-data-row"><span class="hud-data-k">TikTok</span><span class="hud-data-v">12 geplant</span></div><div class="hud-data-desc">Social Media Management.</div>'
        },
        'mod-tasks': {
            title: 'TASKS',
            html: '<div class="hud-data-row"><span class="hud-data-k">Offene Aufgaben</span><span class="hud-data-v">18</span></div><div class="hud-data-row"><span class="hud-data-k">In Arbeit</span><span class="hud-data-v">7</span></div><div class="hud-data-row"><span class="hud-data-k">Heute erledigt</span><span class="hud-data-v">23</span></div><div class="hud-data-desc">Projekt- und Aufgabenverwaltung.</div>'
        },
        'mod-ai': {
            title: 'AI SCOUT',
            html: '<div class="hud-data-row"><span class="hud-data-k">Neue Tools</span><span class="hud-data-v">14</span></div><div class="hud-data-row"><span class="hud-data-k">Top Fund</span><span class="hud-data-v text-cyan">Emergent</span></div><div class="hud-data-desc">Bewertet neue KI-Tools.</div>'
        },
        'mod-video': {
            title: 'VIDEO CONTENT',
            html: '<div class="hud-data-row"><span class="hud-data-k">Status</span><span class="hud-data-v text-green">Aktiv</span></div><div class="hud-data-row"><span class="hud-data-k">Shorts in Prod.</span><span class="hud-data-v">3</span></div><div class="hud-data-desc">Video-Produktion.</div>'
        },
        'mod-paperless': {
            title: 'PAPERLESS',
            html: '<div class="hud-data-row"><span class="hud-data-k">Status</span><span class="hud-data-v text-green">Online</span></div><div class="hud-data-row"><span class="hud-data-k">Dokumente</span><span class="hud-data-v">12.450</span></div><div class="hud-data-desc">Dokumentenverwaltung.</div>'
        },
        'mod-gbrain': {
            title: 'GBRAIN',
            html: '<div class="hud-data-row"><span class="hud-data-k">Status</span><span class="hud-data-v text-green">Online</span></div><div class="hud-data-row"><span class="hud-data-k">Konzepte</span><span class="hud-data-v">980</span></div><div class="hud-data-desc">Wissensdatenbank.</div>'
        }
    };
"""

js_content = re.sub(r'const overlayData = \{.*?\};\s*Object\.keys\(overlayData\)\.forEach\(.*?\}\);', new_overlay_data + """
    Object.keys(overlayData).forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.style.cursor = 'pointer';
            el.addEventListener('click', () => {
                const data = overlayData[id];
                openHud(data.title, data.html);
            });
        }
    });
""", js_content, flags=re.DOTALL)


new_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>RentenPilot – Hermes Command Center</title>
  <link rel="stylesheet" href="{{{{ url_for('static', filename='css/style.css') }}}}" />
</head>
<body>

<div class="scan-lines"></div>

<div id="dashboard">

  <!-- TOP HEADER -->
  <div class="top-header">
    <div class="header-left">
      <div class="logo-box">
        <div class="logo-icon">
            <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M50 10 L90 30 L50 90 L10 30 Z" fill="rgba(0,212,255,0.2)"/>
                <path d="M50 10 L50 90" stroke="rgba(0,212,255,0.5)"/>
            </svg>
        </div>
        <div class="logo-text">
          <div class="logo-title">RENTEN<span>PILOT</span></div>
          <div class="logo-subtitle">HERMES COMMAND CENTER</div>
        </div>
      </div>
      <div class="agent-status">
        <div class="as-label"><span class="dot green-dot small"></span> AGENT STATUS</div>
        <div class="as-val text-green">ONLINE</div>
      </div>
      <div class="aktives-modell">
        <div class="as-label">AKTIVES MODELL</div>
        <div class="as-val" id="live-model">deepseek/deepseek-v4-flash <span class="dim">(via OpenRouter)</span></div>
        <div style="display:none;" id="usage-provider"></div> <!-- Hidden requirement -->
      </div>
    </div>

    <div class="header-right">
      <div class="sys-stat">
        <div class="stat-label">UPTIME</div>
        <div class="stat-val" id="live-uptime">7D 14H 32M</div>
        <div style="display:none;" id="live-hermes-uptime"></div>
      </div>
      <div class="sys-circ">
        <div class="circ-label">CPU</div>
        <div class="circ-val" id="live-cpu">23%</div>
        <div style="display:none;" id="live-cpu-bar"></div>
        <svg class="spark" viewBox="0 0 40 10"><path d="M0,5 L10,2 L20,8 L30,4 L40,6" fill="none" stroke="var(--cyan)"/></svg>
      </div>
      <div class="sys-circ">
        <div class="circ-label">RAM</div>
        <div class="circ-val" id="live-ram">58%</div>
        <div style="display:none;" id="live-ram-bar"></div>
        <svg class="spark" viewBox="0 0 40 10"><path d="M0,8 L10,5 L20,7 L30,2 L40,4" fill="none" stroke="var(--cyan)"/></svg>
      </div>
      <div class="sys-circ">
        <div class="circ-label">DISK</div>
        <div class="circ-val" id="live-disk">41%</div>
        <div style="display:none;" id="live-disk-bar"></div>
        <div style="display:none;" id="disk-gauge-fill"></div>
        <div style="display:none;" id="disk-gauge-val"></div>
        <div style="display:none;" id="disk-total"></div>
        <div style="display:none;" id="disk-free"></div>
      </div>
      <div class="time-box">
        <div id="time-display">15:01:30</div>
        <div class="date-row">
          <span id="date-display">14.05.2025</span>
          <span id="day-display">Sonntag</span>
        </div>
      </div>
    </div>
  </div>

  <!-- MAIN GRID -->
  <div class="main-grid">

    <!-- LEFT COLUMN -->
    <div class="col-left">
      <div class="panel">
        <div class="panel-header">HAUPTMODULE</div>
        <div class="mod-list">
          <!-- Research -->
          <div class="mod-item" id="mod-research">
            <div class="mod-icon">🔍</div>
            <div class="mod-details">
              <div class="mod-title">RESEARCH <span class="mod-status text-green">AKTIV</span></div>
              <div class="mod-row"><span>Neue Themen</span><span>14</span></div>
              <div class="mod-row"><span>Quellen heute</span><span>32</span></div>
              <div class="mod-row"><span>Letzter Scan</span><span>08:42</span></div>
            </div>
            <div class="mod-arrow">›</div>
          </div>
          <!-- Content -->
          <div class="mod-item" id="mod-content">
            <div class="mod-icon">▷</div>
            <div class="mod-details">
              <div class="mod-title">CONTENT <span class="mod-status text-green">AKTIV</span></div>
              <div class="mod-row"><span>Artikel Entwürfe</span><span>7</span></div>
              <div class="mod-row"><span>In Prüfung</span><span>2</span></div>
              <div class="mod-row"><span>Veröffentlicht heute</span><span>1</span></div>
            </div>
            <div class="mod-arrow">›</div>
          </div>
          <!-- Trading -->
          <div class="mod-item" id="mod-trading">
            <div class="mod-icon">⚲</div>
            <div class="mod-details">
              <div class="mod-title">TRADING <span class="mod-status text-green">AKTIV</span></div>
              <div class="mod-row"><span>Aktive Signale</span><span>2</span></div>
              <div class="mod-row"><span>Trefferquote</span><span>71%</span></div>
              <div class="mod-row"><span>Monat</span><span class="text-green">+4.2R</span></div>
            </div>
            <div class="mod-arrow">›</div>
          </div>
        </div>
      </div>

      <div class="panel" style="flex:1;">
        <div class="panel-header">SCHNELLAKTIONEN</div>
        <div class="action-list">
          <button class="action-btn"><span>🔍 Recherche starten</span></button>
          <button class="action-btn"><span>📝 Artikel erstellen</span></button>
          <button class="action-btn"><span>📊 SEO Analyse</span></button>
          <button class="action-btn"><span>📈 Trading Scan</span></button>
          <button class="action-btn"><span>📁 Paperless Import</span></button>
          <div class="action-link">Alle Workflows anzeigen ›</div>
        </div>
      </div>
    </div>

    <!-- CENTER COLUMN -->
    <div class="col-center">
      <div class="sphere-panel">
        <div id="sphere-container">
          <div class="sphere-rings">
            <div class="sphere-ring"></div>
            <div class="sphere-ring"></div>
            <div class="sphere-ring"></div>
          </div>
          <div class="sphere-glow-ring"></div>
          <canvas id="sphere-canvas"></canvas>
          <div class="sphere-overlay-logo">
             <svg viewBox="0 0 100 100" fill="none" stroke="var(--cyan)" stroke-width="2">
                <path d="M50 20 L80 40 L50 80 L20 40 Z" fill="rgba(0,212,255,0.1)"/>
            </svg>
          </div>
          <div id="hermes-status-text" style="display:none;"></div>
        </div>
      </div>

      <div class="chat-panel">
        <div class="chat-header">
          <span>HERMES SPHÄRE – CHAT</span>
          <span class="chat-status"><span class="dot green-dot small"></span> ONLINE</span>
        </div>
        <div class="chat-answer-label" id="chat-answer-label" style="display:none;"></div>
        <div class="chat-answer-box visible" id="chat-answer-box"></div>
        <div style="display:none;" id="live-response-time"></div>
        
        <div class="chat-input-area" style="display:none;">
            <!-- Hidden input but kept for JS compatibility -->
            <input type="text" id="chat-input" placeholder="Sprich oder schreibe mit Hermes..." />
            <button id="send-btn">SENDEN</button>
        </div>

        <div class="chat-controls">
          <button class="ctrl-btn" id="mic-btn">
            <span class="icon">🎤</span>
            <div class="ctrl-text">SPRACH<br>EINGABE</div>
          </button>
          <button class="ctrl-btn" id="kbd-btn" onclick="document.querySelector('.chat-input-area').style.display='flex';document.getElementById('chat-input').focus();">
            <span class="icon">⌨️</span>
            <div class="ctrl-text">TASTATUR<br>MODUS</div>
          </button>
          <button class="ctrl-btn" id="speech-btn">
            <span class="icon">🔊</span>
            <div class="ctrl-text"><br>SPRACHAUSGABE</div>
          </button>
        </div>
      </div>
    </div>

    <!-- RIGHT COLUMN -->
    <div class="col-right">
      <!-- Trading Center -->
      <div class="panel">
        <div class="panel-header">TRADING CENTER <span class="float-right text-green"><span class="dot green-dot small"></span> LIVE</span></div>
        <div class="trading-content">
          <div class="tc-top">
            <div class="tc-pair"><span class="text-orange">BTC</span> / USD <span class="dim">Bitcoin</span></div>
            <div class="tc-spans"><span>1H</span><span>4H</span><span class="active">1D</span><span>1W</span><span>1M</span></div>
          </div>
          <div class="tc-price">67,245.18</div>
          <div class="tc-change text-green">+1,245.32 +1.89%</div>
          <div class="tc-chart">
            <svg viewBox="0 0 200 40" preserveAspectRatio="none">
              <path d="M0,30 Q10,25 20,28 T40,20 T60,25 T80,15 T100,10 T120,18 T140,5 T160,8 T180,2 T200,5" fill="none" stroke="var(--green)" stroke-width="1.5"/>
              <path d="M0,30 Q10,25 20,28 T40,20 T60,25 T80,15 T100,10 T120,18 T140,5 T160,8 T180,2 T200,5 L200,40 L0,40 Z" fill="url(#greenGrad)" opacity="0.3"/>
              <defs>
                <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="var(--green)"/>
                  <stop offset="100%" stop-color="transparent"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div class="tc-signal">
            <div class="sig-badge">LONG</div>
            <div class="sig-conf">CONFIDENCE<br><span class="text-green">84%</span></div>
          </div>
          <div class="tc-levels">
            <div><span class="dim">ENTRY</span><br>67,120.00</div>
            <div><span class="dim">SL</span><br><span class="text-orange">65,800.00</span></div>
            <div><span class="dim">TP1</span><br><span class="text-green">68,500.00</span></div>
            <div><span class="dim">TP2</span><br><span class="text-green">70,200.00</span></div>
            <div><span class="dim">STATUS</span><br><span class="text-green">ACTIVE <span class="dot green-dot small"></span></span></div>
          </div>
        </div>
      </div>

      <!-- Kosten & Guthaben -->
      <div class="panel">
        <div class="panel-header">KOSTEN & GUTHABEN – OPENROUTER</div>
        <div class="cost-grid">
          <div class="cost-box">
            <div class="cb-label">VERBRAUCH HEUTE</div>
            <div class="cb-val text-cyan" id="usage-cost-today">$0.02</div>
            <div class="cb-sub text-green">+5% <span class="dim">vs gestern</span></div>
            <div style="display:none;" id="usage-cost-total"></div>
          </div>
          <div class="cost-box">
            <div class="cb-label">VERBRAUCH MONAT</div>
            <div class="cb-val text-cyan" id="usage-cost-month">$0.42</div>
            <div class="cb-sub text-green">+12% <span class="dim">vs Vormonat</span></div>
          </div>
          <div class="cost-box last">
            <div class="cb-label">GUTHABEN</div>
            <div class="cb-val text-cyan" id="usage-credit">$8.72</div>
            <div class="cb-circle"><span>87%</span><br><span style="font-size:5px">verfügbar</span></div>
          </div>
          <div class="cost-legend">
            <div><span class="dot green-dot small"></span> > $10</div>
            <div><span class="dot" style="background:#ffcc00"></span> $5 - $10</div>
            <div><span class="dot" style="background:var(--orange)"></span> < $5</div>
          </div>
        </div>
      </div>

      <!-- Agenten & Quality -->
      <div class="split-panels">
        <div class="panel" style="padding:10px;">
          <div class="panel-header" style="margin-bottom:6px;">HERMES AGENTEN</div>
          <div class="agent-list" id="hi-agents-container">
            <div class="al-row"><input type="checkbox" checked disabled> <span>Research Agent</span> <span class="text-green">Läuft ›</span></div>
            <div class="al-row"><input type="checkbox" checked disabled> <span>Content Agent</span> <span class="text-green">Läuft ›</span></div>
            <div class="al-row"><input type="checkbox" checked disabled> <span>SEO Agent</span> <span class="text-orange">Wartet ›</span></div>
            <div class="al-row"><input type="checkbox" checked disabled> <span>Publisher Agent</span> <span class="text-green">Läuft ›</span></div>
            <div class="al-row"><input type="checkbox" checked disabled> <span>Social Agent</span> <span class="text-orange">Wartet ›</span></div>
            <div class="al-row"><input type="checkbox" checked disabled> <span>Trading Agent</span> <span class="text-cyan">Aktiv ›</span></div>
            <div class="al-row"><input type="checkbox" checked disabled> <span>Fact Check Agent</span> <span class="text-cyan">Aktiv ›</span></div>
            <div class="al-row"><input type="checkbox" checked disabled> <span>Legal Agent</span> <span class="text-orange">Wartet ›</span></div>
            <!-- Hidden requirements -->
            <div style="display:none;" id="hi-version"></div>
            <div style="display:none;" id="hi-agents"></div>
            <div style="display:none;" id="hi-skills"></div>
          </div>
        </div>
        <div class="panel" style="padding:10px;">
          <div class="panel-header" style="margin-bottom:6px;">QUALITY CONTROL</div>
          <div class="qc-list">
            <div class="qc-row"><span class="icon text-green">✔</span> Generator <span class="float-right text-green">✔</span></div>
            <div class="qc-row"><span class="icon text-green">✔</span> Critic <span class="float-right text-green">✔</span></div>
            <div class="qc-row"><span class="icon text-green">✔</span> Fact Check <span class="float-right text-green">✔</span></div>
            <div class="qc-row"><span class="icon text-green">✔</span> Judge <span class="float-right text-green">✔</span></div>
          </div>
          <div class="qc-rate">
            <span>Freigaberate</span>
            <span class="text-green" style="font-size:14px; font-weight:bold;">94%</span>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- WEITERE MODULE -->
  <div class="bottom-modules">
    <div class="panel bmod" id="mod-publisher">
      <div class="bmod-head">📄 PUBLISHER</div>
      <div class="bmod-row"><span>Artikel veröffentlicht</span></div>
      <div class="bmod-row"><span>Heute:</span><span>3</span></div>
      <div class="bmod-row"><span>Geplant</span><span>5</span></div>
      <div class="bmod-row"><span>Nächste</span><span>09:00 Uhr</span></div>
    </div>
    <div class="panel bmod" id="mod-social">
      <div class="bmod-head">👥 SOCIAL MEDIA</div>
      <div class="bmod-row"><span>TikTok</span><span class="text-green">12 geplant</span></div>
      <div class="bmod-row"><span>Instagram</span><span>8 geplant</span></div>
      <div class="bmod-row"><span>Facebook</span><span>4 geplant</span></div>
    </div>
    <div class="panel bmod" id="mod-tasks">
      <div class="bmod-head">📋 TASKS</div>
      <div class="bmod-row"><span>Offene Aufgaben</span><span>18</span></div>
      <div class="bmod-row"><span>In Arbeit</span><span>7</span></div>
      <div class="bmod-row"><span>Erledigt heute</span><span>23</span></div>
    </div>
    <div class="panel bmod">
      <div class="bmod-head">📖 TRADE JOURNAL</div>
      <div class="bmod-row"><span>Trades gesamt</span><span>124</span></div>
      <div class="bmod-row"><span>Gewonnen</span><span>87</span></div>
      <div class="bmod-row"><span>Verloren</span><span>37</span></div>
      <div class="bmod-row"><span>Trefferquote</span><span>70.1%</span></div>
    </div>
    <div class="panel bmod" id="mod-paperless">
      <div class="bmod-head">📁 PAPERLESS</div>
      <div class="bmod-row"><span>Dokumente</span><span>12.450</span></div>
      <div class="bmod-row"><span>Neue Dokumente</span><span>17</span></div>
      <div class="bmod-row"><span>OCR Queue</span><span>3</span></div>
      <div class="bmod-row"><span>Status</span><span class="text-green">Online</span></div>
    </div>
    <div class="panel bmod" id="mod-gbrain">
      <div class="bmod-head">🌐 GBRAIN</div>
      <div class="bmod-row"><span>Quellen</span><span>4.120</span></div>
      <div class="bmod-row"><span>Personen</span><span>620</span></div>
      <div class="bmod-row"><span>Firmen</span><span>380</span></div>
      <div class="bmod-row"><span>Konzepte</span><span>980</span></div>
      <div class="bmod-row"><span>Status</span><span class="text-green">Online</span></div>
    </div>
    <div class="panel bmod" id="mod-ai">
      <div class="bmod-head">🔍 AI SCOUT</div>
      <div class="bmod-row"><span>Neue Tools</span><span>14</span></div>
      <div class="bmod-row"><span>Bewertet</span><span>8</span></div>
      <div class="bmod-row"><span>Interessant</span><span>3</span></div>
      <div class="bmod-row"><span>Top Fund</span><span class="text-green">Emergent</span></div>
    </div>
    <div class="panel bmod" id="mod-video">
      <div class="bmod-head">🎬 VIDEO CONTENT</div>
      <div class="bmod-row"><span>YouTube Shorts</span><span>7</span></div>
      <div class="bmod-row"><span>TikTok Skripte</span><span>12</span></div>
      <div class="bmod-row"><span>In Produktion</span><span>3</span></div>
      <div class="bmod-row"><span>Status</span><span class="text-green">Aktiv</span></div>
    </div>
  </div>

  <!-- FOOTER -->
  <div class="footer-bar">
    <div class="fb-left">
      <span>LETZTES UPDATE</span><br>
      <span class="dim">14.05.2025 - 15:01:30</span>
    </div>
    <div class="fb-center">
      <svg viewBox="0 0 20 20" width="16" height="16" fill="var(--cyan)"><path d="M10 2 L18 6 L10 18 L2 6 Z"/></svg>
      HERMES DENKT. HERMES HANDELT. HERMES LIEFERT.
    </div>
    <div class="fb-right">
      <span style="font-size:14px">🔒</span>
      <div>
        SICHER & PRIVAT<br>
        <span class="text-green">ALLE SYSTEME VERSCHLÜSSELT</span>
      </div>
    </div>
  </div>

</div><!-- /dashboard -->

<!-- HUD OVERLAY -->
<div id="hud-overlay" class="hud-overlay">
  <div class="hud-overlay-box">
    <button class="hud-close-btn" id="hud-close-btn">×</button>
    <div class="hud-overlay-header">
      <span class="hud-overlay-title" id="hud-overlay-title">MODUL</span>
    </div>
    <div class="hud-overlay-content" id="hud-overlay-content">
      <!-- Content dynamically injected here -->
    </div>
  </div>
</div>

{js_content}

</body>
</html>
"""

new_css = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');

:root {
  --bg-dark: #020712;
  --bg-panel: rgba(4, 18, 42, 0.6);
  --cyan: #00d4ff;
  --blue: #0055ff;
  --green: #00ff66;
  --orange: #ff6000;
  --text-primary: #c8e6f5;
  --text-secondary: rgba(170, 210, 240, 0.6);
  --border: rgba(0, 212, 255, 0.15);
}

* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Rajdhani', sans-serif; }
body { background: var(--bg-dark); color: var(--text-primary); overflow: hidden; font-size: 11px; }

/* Grid overlay */
body::before {
  content: ''; position: fixed; inset: 0; z-index: 0;
  background-image: linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
  background-size: 48px 48px; pointer-events: none;
}

#dashboard {
  position: relative; z-index: 1; display: flex; flex-direction: column; width: 100vw; height: 100vh; padding: 8px; gap: 8px;
}

/* TOP HEADER */
.top-header {
  display: flex; justify-content: space-between; align-items: center; height: 50px; flex-shrink: 0; padding: 0 10px;
}

.header-left { display: flex; align-items: center; gap: 20px; }
.logo-box { display: flex; align-items: center; gap: 10px; }
.logo-icon { width: 36px; height: 36px; }
.logo-title { font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 800; letter-spacing: 2px; color: #fff; line-height: 1; }
.logo-title span { color: var(--cyan); }
.logo-subtitle { font-family: 'Orbitron', sans-serif; font-size: 8px; color: var(--cyan); letter-spacing: 2px; }

.agent-status { border-left: 1px solid var(--border); padding-left: 20px; }
.as-label { font-size: 8px; color: var(--text-secondary); margin-bottom: 2px; text-transform: uppercase; }
.as-val { font-size: 14px; font-weight: 700; font-family: 'Orbitron', sans-serif; letter-spacing: 1px; }

.aktives-modell { border-left: 1px solid var(--border); padding-left: 20px; }

.header-right { display: flex; align-items: center; gap: 20px; }
.sys-stat, .sys-circ { display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; }
.stat-label, .circ-label { font-size: 8px; color: var(--text-secondary); text-transform: uppercase; }
.stat-val { font-size: 14px; font-weight: 700; font-family: 'Orbitron', sans-serif; }
.circ-val { font-size: 14px; font-weight: 700; font-family: 'Orbitron', sans-serif; }
.spark { width: 40px; height: 10px; margin-top: 2px; }

.sys-circ { width: 40px; height: 40px; border: 1px solid var(--border); border-radius: 50%; }

.time-box { text-align: right; border-left: 1px solid var(--border); padding-left: 20px; }
#time-display { font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 700; color: var(--cyan); line-height: 1; }
.date-row { font-size: 10px; color: var(--text-secondary); }

/* MAIN GRID */
.main-grid {
  display: grid; grid-template-columns: 240px 1fr 300px; gap: 10px; flex: 1; min-height: 0;
}

.panel {
  background: var(--bg-panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px;
  display: flex; flex-direction: column; position: relative; overflow: hidden; backdrop-filter: blur(10px);
}
.panel::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--cyan), transparent);
}
.panel-header {
  font-family: 'Orbitron', sans-serif; font-size: 10px; color: var(--text-secondary); letter-spacing: 2px;
  border-bottom: 1px solid rgba(0,212,255,0.1); padding-bottom: 6px; margin-bottom: 10px; text-transform: uppercase;
}

/* COL LEFT */
.col-left { display: flex; flex-direction: column; gap: 10px; }
.mod-list { display: flex; flex-direction: column; gap: 10px; }
.mod-item {
  display: flex; gap: 10px; padding: 8px; border: 1px solid transparent; border-radius: 4px;
  background: rgba(0,212,255,0.03); cursor: pointer; transition: all 0.2s; position: relative;
}
.mod-item:hover { border-color: var(--cyan); background: rgba(0,212,255,0.08); }
.mod-icon {
  width: 32px; height: 32px; border: 1px solid var(--cyan); border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 14px; color: var(--cyan); flex-shrink: 0; box-shadow: 0 0 10px rgba(0,212,255,0.2);
}
.mod-details { flex: 1; }
.mod-title { font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700; margin-bottom: 4px; display: flex; justify-content: space-between; }
.mod-status { font-size: 8px; }
.mod-row { display: flex; justify-content: space-between; font-size: 9px; color: var(--text-secondary); margin-bottom: 2px; }
.mod-row span:last-child { color: var(--text-primary); font-weight: 600; }
.mod-arrow { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); color: var(--cyan); font-size: 16px; opacity: 0; transition: 0.2s; }
.mod-item:hover .mod-arrow { opacity: 1; right: 6px; }

.action-list { display: flex; flex-direction: column; gap: 6px; }
.action-btn {
  background: rgba(0,212,255,0.05); border: 1px solid rgba(0,212,255,0.2); border-radius: 4px; padding: 8px 12px;
  color: var(--text-primary); text-align: left; cursor: pointer; font-size: 11px; transition: 0.2s;
}
.action-btn:hover { background: rgba(0,212,255,0.15); border-color: var(--cyan); }
.action-link { font-size: 9px; color: var(--cyan); text-align: center; margin-top: 10px; cursor: pointer; }

/* COL CENTER */
.col-center { display: flex; flex-direction: column; gap: 10px; }
.sphere-panel { flex: 1; background: radial-gradient(circle at center, rgba(0,85,255,0.1) 0%, transparent 70%); position: relative; border-radius: 6px; border: 1px solid var(--border); }
#sphere-container { width: 100%; height: 100%; position: relative; display: flex; align-items: center; justify-content: center; }
.sphere-rings { position: absolute; width: 300px; height: 300px; border-radius: 50%; border: 1px dashed rgba(0,212,255,0.2); transform: rotateX(70deg); bottom: -100px; }
.sphere-ring { position: absolute; inset: 0; border: 1px solid var(--cyan); border-radius: 50%; box-shadow: 0 0 20px var(--cyan); }
.sphere-ring:nth-child(2) { inset: 20px; }
.sphere-ring:nth-child(3) { inset: 40px; }
.sphere-glow-ring { position: absolute; width: 250px; height: 250px; border-radius: 50%; box-shadow: 0 0 80px var(--blue); }
#sphere-canvas { position: relative; z-index: 2; width: 250px; height: 250px; }
.sphere-overlay-logo { position: absolute; width: 80px; height: 80px; z-index: 3; filter: drop-shadow(0 0 10px var(--cyan)); }

.chat-panel { height: 220px; background: var(--bg-panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.chat-header { display: flex; justify-content: space-between; font-family: 'Orbitron', sans-serif; font-size: 10px; color: var(--text-secondary); border-bottom: 1px solid rgba(0,212,255,0.1); padding-bottom: 6px; }
.chat-answer-box { flex: 1; overflow-y: auto; font-size: 12px; line-height: 1.5; padding-right: 10px; }
.chat-controls { display: flex; gap: 10px; }
.ctrl-btn {
  flex: 1; background: rgba(0,212,255,0.05); border: 1px solid var(--border); border-radius: 6px; padding: 10px;
  display: flex; align-items: center; justify-content: center; gap: 10px; color: var(--text-primary); cursor: pointer; transition: 0.2s;
}
.ctrl-btn:hover { border-color: var(--cyan); background: rgba(0,212,255,0.1); }
.ctrl-text { font-family: 'Orbitron', sans-serif; font-size: 9px; text-align: left; line-height: 1.2; letter-spacing: 1px; }
.ctrl-btn .icon { font-size: 20px; color: var(--cyan); }

.msg-row { margin-bottom: 6px; }
.msg-user { color: var(--cyan); }
.msg-user::before { content: 'Du: '; font-weight: bold; }
.msg-hermes { color: var(--text-primary); }
.msg-hermes::before { content: 'Hermes: '; color: var(--cyan); font-weight: bold; }
.chat-input-area { display: flex; gap: 6px; margin-bottom: 5px; }
#chat-input { flex: 1; background: rgba(0,0,0,0.5); border: 1px solid var(--cyan); border-radius: 4px; color: #fff; padding: 8px; outline: none; }
#send-btn { background: rgba(0,212,255,0.2); border: 1px solid var(--cyan); color: var(--cyan); padding: 8px 12px; border-radius: 4px; font-family: 'Orbitron', sans-serif; cursor: pointer; }

/* COL RIGHT */
.col-right { display: flex; flex-direction: column; gap: 10px; }
.trading-content { display: flex; flex-direction: column; gap: 6px; }
.tc-top { display: flex; justify-content: space-between; align-items: center; }
.tc-pair { font-size: 14px; font-weight: 700; }
.tc-spans { display: flex; gap: 4px; font-size: 8px; }
.tc-spans span { padding: 2px 4px; background: rgba(255,255,255,0.05); border-radius: 2px; }
.tc-spans span.active { background: var(--cyan); color: #000; }
.tc-price { font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 700; color: var(--green); line-height: 1; }
.tc-change { font-size: 10px; }
.tc-chart { height: 40px; margin: 4px 0; }
.tc-chart svg { width: 100%; height: 100%; }
.tc-signal { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-bottom: 6px; }
.sig-badge { background: rgba(0,255,102,0.2); border: 1px solid var(--green); color: var(--green); padding: 4px 12px; font-family: 'Orbitron', sans-serif; font-weight: 700; border-radius: 4px; }
.sig-conf { font-size: 9px; text-align: right; }
.tc-levels { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; font-size: 10px; font-weight: 600; text-align: center; }

.cost-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.cost-box { flex: 1 1 45%; background: rgba(0,0,0,0.3); border: 1px solid rgba(0,212,255,0.1); border-radius: 4px; padding: 8px; display: flex; flex-direction: column; justify-content: space-between; position: relative; }
.cost-box.last { flex: 1 1 100%; display: flex; flex-direction: row; align-items: center; justify-content: space-between; padding-right: 20px; }
.cb-label { font-size: 8px; color: var(--text-secondary); margin-bottom: 4px; }
.cb-val { font-family: 'Orbitron', sans-serif; font-size: 18px; font-weight: 700; }
.cb-sub { font-size: 9px; }
.cb-circle { width: 40px; height: 40px; border: 3px solid var(--blue); border-top-color: var(--cyan); border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; position: absolute; right: 10px; top: 10px; }

.cost-legend { width: 100%; display: flex; justify-content: flex-end; gap: 10px; font-size: 8px; margin-top: 4px; }

.split-panels { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; flex: 1; }
.agent-list { display: flex; flex-direction: column; gap: 4px; }
.al-row { display: flex; align-items: center; gap: 6px; font-size: 10px; padding: 4px; background: rgba(255,255,255,0.02); border-radius: 2px; }
.al-row input { accent-color: var(--cyan); }
.al-row span:last-child { margin-left: auto; font-size: 9px; }

.qc-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.qc-row { font-size: 10px; padding-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.05); }
.qc-rate { border-top: 1px solid var(--cyan); padding-top: 4px; display: flex; justify-content: space-between; align-items: center; font-size: 10px; }

/* BOTTOM MODULES */
.bottom-modules { display: grid; grid-template-columns: repeat(8, 1fr); gap: 10px; height: 90px; flex-shrink: 0; }
.bmod { padding: 8px; display: flex; flex-direction: column; gap: 2px; cursor: pointer; transition: 0.2s; background: var(--bg-panel); border: 1px solid var(--border); border-radius: 6px; backdrop-filter: blur(10px); }
.bmod:hover { border-color: var(--cyan); background: rgba(0,212,255,0.05); }
.bmod-head { font-family: 'Orbitron', sans-serif; font-size: 9px; color: var(--cyan); margin-bottom: 6px; }
.bmod-row { display: flex; justify-content: space-between; font-size: 9px; color: var(--text-secondary); }
.bmod-row span:last-child { color: var(--text-primary); font-weight: 600; }

/* FOOTER */
.footer-bar { display: flex; justify-content: space-between; align-items: center; height: 40px; padding: 0 20px; flex-shrink: 0; }
.fb-left { font-size: 9px; }
.fb-center { font-family: 'Orbitron', sans-serif; font-size: 12px; font-weight: 700; color: var(--text-secondary); letter-spacing: 4px; display: flex; align-items: center; gap: 10px; }
.fb-right { display: flex; align-items: center; gap: 10px; font-size: 9px; font-weight: 600; text-align: right; }

/* UTILS */
.text-cyan { color: var(--cyan); }
.text-green { color: var(--green); }
.text-orange { color: var(--orange); }
.dim { color: var(--text-secondary); }
.float-right { float: right; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.green-dot { background: var(--green); box-shadow: 0 0 6px var(--green); }
.dot.small { width: 5px; height: 5px; }

/* HUD OVERLAY */
.hud-overlay { position: fixed; inset: 0; z-index: 9999; display: flex; align-items: center; justify-content: center; background: rgba(2, 7, 18, 0.6); backdrop-filter: blur(8px); opacity: 0; pointer-events: none; transition: 0.3s; }
.hud-overlay.active { opacity: 1; pointer-events: auto; }
.hud-overlay-box { position: relative; width: 400px; max-width: 90%; background: var(--bg-panel); border: 1px solid var(--cyan); border-radius: 6px; padding: 20px; transform: scale(0.95) translateY(10px); transition: 0.3s; }
.hud-overlay.active .hud-overlay-box { transform: scale(1) translateY(0); }
.hud-close-btn { position: absolute; top: 10px; right: 12px; background: none; border: none; color: var(--cyan); font-size: 24px; cursor: pointer; }
.hud-overlay-header { margin-bottom: 15px; border-bottom: 1px solid rgba(0, 212, 255, 0.2); padding-bottom: 8px; }
.hud-overlay-title { font-family: 'Orbitron', sans-serif; font-size: 14px; font-weight: 700; color: var(--cyan); letter-spacing: 3px; }
.hud-overlay-content { display: flex; flex-direction: column; gap: 10px; }
.hud-data-row { display: flex; justify-content: space-between; font-size: 14px; border-bottom: 1px solid rgba(0,212,255,0.05); padding-bottom: 4px; }
.hud-data-k { color: var(--text-secondary); text-transform: uppercase; }
.hud-data-v { font-weight: 700; color: #fff; }
.hud-data-desc { margin-top: 10px; font-size: 12px; color: var(--text-secondary); background: rgba(0,212,255,0.05); padding: 8px; border-left: 2px solid var(--cyan); }
.hud-action-btn { margin-top: 15px; background: rgba(0,212,255,0.1); border: 1px solid var(--cyan); color: var(--cyan); font-family: 'Orbitron', sans-serif; padding: 8px 16px; cursor: pointer; }

/* SCROLLBAR */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.25); border-radius: 2px; }

#chat-answer-box::-webkit-scrollbar { width: 3px; }
#chat-answer-box::-webkit-scrollbar-thumb { background: var(--cyan); border-radius: 2px; }
.terminal-cursor { display: inline-block; width: 6px; height: 12px; background: var(--cyan); animation: blink 1s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }

/* CHAT MESSAGES */
.msg-thinking { font-style: italic; color: var(--text-secondary); animation: thinkingPulse 1.5s infinite; }
@keyframes thinkingPulse { 50% { opacity: 0.5; } }
.msg-error { color: var(--orange); }
.msg-system { color: var(--green); }
#mic-btn.mic-active { border-color: var(--cyan); color: var(--cyan); box-shadow: 0 0 10px var(--cyan); }
#speech-btn.speech-active { border-color: var(--green); color: var(--green); box-shadow: 0 0 10px var(--green); }
#kbd-btn.active { border-color: var(--blue); color: var(--blue); box-shadow: 0 0 10px var(--blue); }

.sphere-thinking .sphere-glow-ring { border-color: rgba(0,255,255,0.4); box-shadow: 0 0 60px rgba(0,255,255,0.4); }
.sphere-error .sphere-glow-ring { border-color: rgba(255,96,0,0.5); box-shadow: 0 0 60px rgba(255,96,0,0.5); }
.sphere-speaking .sphere-glow-ring { border-color: rgba(168,85,247,0.5); box-shadow: 0 0 60px rgba(168,85,247,0.4); }
.sphere-listening .sphere-glow-ring { border-color: rgba(0,255,102,0.5); box-shadow: 0 0 60px rgba(0,255,102,0.4); }
"""

with open(index_path, "w", encoding="utf-8") as f:
    f.write(new_html)

with open(style_path, "w", encoding="utf-8") as f:
    f.write(new_css)

print("Rewrite successful.")
