# Dashboard Component Contract

Verbindliche Schnittstelle zwischen Layout, JavaScript, APIs und Overlays.

## Vertragsregeln

- `click_target_id` ist bei klickbaren Komponenten identisch mit dem sichtbaren Kachel- oder Button-Element.
- Keine Gruppen-Hotspots.
- Keine Container-Hotspots.
- Keine unsichtbaren Overlay-Flächen.
- Jede sichtbare Kachel ist genau ein eigener Klickbereich.

## Komponentenvertrag

| component_id | visible_label | html_id | css_class | click_target_id | overlay_id | data_source | update_function | api_route | fallback_data | real_data_status | allowed_actions | forbidden_actions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `mod-research` | Research | `mod-research` | `mod-item` | `mod-research` | `overlay-research` | Research/Workflow-Daten | `openOverlay` / `loadResearchData` | später Research-API | Dummy-Kennzahlen | später | Overlay öffnen, Details ansehen | Gruppen-Hotspot, Auto-Action |
| `mod-content` | Content | `mod-content` | `mod-item` | `mod-content` | `overlay-content` | Content/Workflow-Daten | `openOverlay` / `loadContentData` | später Content-API | Dummy-Kennzahlen | später | Overlay öffnen, Details ansehen | Gruppen-Hotspot, Auto-Action |
| `mod-trading` | Trading | `mod-trading` | `mod-item` | `mod-trading` | `overlay-trading` | Trading-Read-Daten | `openOverlay` / `loadTradingSummary` | später `/api/trading/live?symbol=...` | Dummy-Signale | später | Overlay öffnen, read-only Details | Order-Ausführung, Auto-Handlung |
| `action-research` | Recherche starten | `action-research` | `action-btn` | `action-research` | `overlay-action-research` | Workflow-Aktion | `startWorkflowOverlay` | keine / später Workflow-API | Lokaler Dummy-Flow | später | Workflow-Overlay öffnen | Gruppen-Hotspot, Backend-Neubau |
| `action-article` | Artikel erstellen | `action-article` | `action-btn` | `action-article` | `overlay-action-article` | Workflow-Aktion | `startWorkflowOverlay` | keine / später Workflow-API | Lokaler Dummy-Flow | später | Workflow-Overlay öffnen | Gruppen-Hotspot, Backend-Neubau |
| `action-seo` | SEO Analyse | `action-seo` | `action-btn` | `action-seo` | `overlay-action-seo` | Workflow-Aktion | `startWorkflowOverlay` | keine / später Workflow-API | Lokaler Dummy-Flow | später | Workflow-Overlay öffnen | Gruppen-Hotspot, Backend-Neubau |
| `action-trading-scan` | Trading Scan | `action-trading-scan` | `action-btn` | `action-trading-scan` | `overlay-action-trading-scan` | Workflow-Aktion | `startWorkflowOverlay` | keine / später Workflow-API | Lokaler Dummy-Flow | später | Scan-Overlay öffnen | Order-Ausführung, Auto-Handlung |
| `action-paperless-import` | Paperless Import | `action-paperless-import` | `action-btn` | `action-paperless-import` | `overlay-action-paperless-import` | Workflow-Aktion | `startWorkflowOverlay` | keine / später Workflow-API | Lokaler Dummy-Flow | später | Import-Overlay öffnen | Gruppen-Hotspot, Backend-Neubau |
| `action-workflows` | Alle Workflows anzeigen | `action-workflows` | `action-link` | `action-workflows` | `overlay-workflows` | Workflow-Übersicht | `openWorkflowOverview` | keine / später Workflow-API | Lokaler Dummy-Flow | später | Workflow-Übersicht öffnen | Gruppen-Hotspot, direkte Ausführung |
| `sphere-container` | Hermes Sphäre | `sphere-container` | `sphere-panel` / `sphere-container` | `sphere-container` | `overlay-sphere` | Hermes-/Systemzustände | `setSphereState` / `renderSphere` | `/api/system` plus lokale Zustände | Idle/Thinking/Listening/Speaking/Error | ja | Status anzeigen, Overlay öffnen | Layout verändern, Agentenlogik neu bauen |
| `chat-panel` | Chatbereich | `chat-panel` | `chat-panel` | `chat-panel` | `overlay-chat` | Chat- und Antwortdaten | `sendMessage` / `renderHistory` | `/api/chat` | Lokaler Chatverlauf, Default-Antwort | ja | Chat senden, Verlauf ansehen, Overlay öffnen | Gruppen-Hotspot, API-Logik ändern |
| `mic-btn` | Spracheingabe | `mic-btn` | `ctrl-btn` | `mic-btn` | `overlay-mic` | Browser SpeechRecognition | `toggleListening` | keine neue API | Browser-Fallback-Meldung | ja | Aufnahme starten/stoppen | Gruppen-Hotspot, Backend-Neubau |
| `kbd-btn` | Tastaturmodus | `kbd-btn` | `ctrl-btn` | `kbd-btn` | `overlay-keyboard` | UI-Interaktion | `enableKeyboardMode` | keine | Fokus auf Eingabe, UI-Zustand | ja | Texteingabe aktivieren | Gruppen-Hotspot, Auto-Workflow |
| `speech-btn` | Sprachausgabe | `speech-btn` | `ctrl-btn` | `speech-btn` | `overlay-speech` | SpeechSynthesis / optional TTS | `toggleSpeechOutput` | optional `/api/tts` | Browser SpeechSynthesis | ja | Ausgabe ein-/ausschalten | Gruppen-Hotspot, Backend-Neubau |
| `panel-trading-center` | Trading Center | `panel-trading-center` | `panel-trading` | `panel-trading-center` | `overlay-trading-center` | Trading-Read-Daten | `updateTradingCenter` | später `/api/trading/live?symbol=...` | Statische Marktwerte | später | read-only Details, Symbol-Overlay | Order-Ausführung, Auto-Handlung |
| `panel-openrouter` | Kosten & Guthaben / OpenRouter | `panel-openrouter` | `cost-grid cost-grid-simple` | `panel-openrouter` | `overlay-openrouter` | OpenRouter-/Usage-Daten | `updateOpenRouterData` / `updateUsageData` | `/api/openrouter`, `/api/usage` | Verbrauch heute, Verbrauch Monat, Guthaben, optional Gesamtverbrauch | ja | Daten anzeigen, Overlay öffnen | Kreisgrafik erzwingen, andere APIs |
| `panel-hermes-agents` | Hermes Agenten | `panel-hermes-agents` | `panel` | `panel-hermes-agents` | `overlay-hermes-agents` | Hermes-Status | `updateHermesStatus` | `/api/hermes_status` | Agentenliste, Statusfarben | ja | Status anzeigen, Overlay öffnen | Agentenlogik in Flask nachbauen |
| `panel-quality-control` | Quality Control | `panel-quality-control` | `panel` | `panel-quality-control` | `overlay-quality-control` | QC-/Freigabedaten | `updateQualityControl` | später QC-API | Dummy-Prüfstatus | später | Overlay öffnen, Status lesen | Gruppen-Hotspot, Automatisierung |
| `mod-publisher` | Publisher | `mod-publisher` | `bmod` | `mod-publisher` | `overlay-publisher` | Publish-/Content-Daten | `openOverlay` / `loadPublisherData` | später Publish-API | Dummy-Kennzahlen | später | Overlay öffnen | Gruppen-Hotspot |
| `mod-social` | Social Media | `mod-social` | `bmod` | `mod-social` | `overlay-social` | Social-Daten | `openOverlay` / `loadSocialData` | später Social-API | Dummy-Kennzahlen | später | Overlay öffnen | Gruppen-Hotspot |
| `mod-tasks` | Tasks | `mod-tasks` | `bmod` | `mod-tasks` | `overlay-tasks` | Task-Daten | `openOverlay` / `loadTaskData` | später Task-API | Dummy-Kennzahlen | später | Overlay öffnen | Gruppen-Hotspot |
| `mod-tradejournal` | Trade Journal | `mod-tradejournal` | `bmod` | `mod-tradejournal` | `overlay-tradejournal` | Journal-Daten | `openOverlay` / `loadTradeJournalData` | später Journal-API | Dummy-Kennzahlen | später | Overlay öffnen | Gruppen-Hotspot |
| `mod-paperless` | Paperless | `mod-paperless` | `bmod` | `mod-paperless` | `overlay-paperless` | Paperless-Daten | `openOverlay` / `loadPaperlessData` | später Paperless-API | Dummy-Kennzahlen | später | Overlay öffnen | Gruppen-Hotspot |
| `mod-gbrain` | GBrain | `mod-gbrain` | `bmod` | `mod-gbrain` | `overlay-gbrain` | Wissensdaten | `openOverlay` / `loadGbrainData` | später Knowledge-API | Dummy-Kennzahlen | später | Overlay öffnen | Gruppen-Hotspot |
| `mod-ai` | AI Scout | `mod-ai` | `bmod` | `mod-ai` | `overlay-ai-scout` | Scouting-Daten | `openOverlay` / `loadAiScoutData` | später Scout-API | Dummy-Kennzahlen | später | Overlay öffnen | Gruppen-Hotspot |
| `mod-video` | Video Content | `mod-video` | `bmod` | `mod-video` | `overlay-video-content` | Video-Content-Daten | `openOverlay` / `loadVideoContentData` | später Video-API | Dummy-Kennzahlen | später | Overlay öffnen | Gruppen-Hotspot |

## Sonderregeln

- `panel-openrouter` zeigt nur OpenRouter-Daten.
- `panel-openrouter` erzwingt keine Kreisgrafik.
- Pflichtwerte für `panel-openrouter`: Verbrauch heute, Verbrauch Monat, Guthaben, optional Gesamtverbrauch.
- `panel-trading-center` bleibt read-only.
- `panel-trading-center` führt keine Orders aus und triggert keine automatische Handlung.
- `panel-trading-center` bereitet Asset-Auswahl für GOLD, GER40, US500, EURUSD, GBPUSD, BTCUSD und ETHUSD vor.
- `sphere-container` kennt die Statuszustände `idle`, `listening`, `thinking`, `speaking`, `error`.
- `chat-panel` nutzt `/api/chat` und liest Antworten aus `data.answer`, `data.response`, `data.result`, `data.message`.
- `panel-hermes-agents` nutzt `/api/hermes_status`.
- Hermes bleibt Agentensystem.
- Flask bleibt Anzeige- und API-Brücke.
- Keine Agentenlogik in Flask nachbauen.

