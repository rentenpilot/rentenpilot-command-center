# Dashboard Overlays

Referenz: `reference/Hermes Dashboard.png`

## Leitregel
Jede klickbare Kachel besitzt später genau ein eigenes Overlay. Keine Gruppen-Overlays.

## Overlay-Inventar

| Klickbare Kachel | Overlay-ID | Titel | Angezeigte Detaildaten | Spätere Aktionen | Spätere API | Workflow starten |
|---|---|---|---|---|---|---|
| `mod-research` | `overlay-research` | Research | Themen, Quellen, Scan-Zeit, Status | Recherche öffnen, Quellen filtern | spätere Research-API | ja |
| `mod-content` | `overlay-content` | Content | Entwürfe, Prüfung, Veröffentlichungen | Content-Liste öffnen, Entwurf anlegen | spätere Content-API | ja |
| `mod-trading` | `overlay-trading` | Trading | Signale, Trefferquote, Monatswerte | Trading-Detailansicht, Signal-Übersicht | spätere Trading-Read-API | nein |
| `action-research` | `overlay-action-research` | Recherche starten | Workflow-Ziel, Kontext, Parameter | Recherche-Workflow starten | Workflow-API oder lokale Aktion | ja |
| `action-article` | `overlay-action-article` | Artikel erstellen | Vorlagen, Status, Zielkanal | Artikel-Workflow starten | Workflow-API oder lokale Aktion | ja |
| `action-seo` | `overlay-action-seo` | SEO Analyse | Seiten, Score, Empfehlungen | Analyse starten | Workflow-API oder lokale Aktion | ja |
| `action-trading-scan` | `overlay-action-trading-scan` | Trading Scan | Instrumente, Signale, Zeitraum | Scan starten | Workflow-API oder lokale Aktion | ja |
| `action-paperless-import` | `overlay-action-paperless-import` | Paperless Import | Dokumente, Queue, Status | Import anstoßen | Workflow-API oder lokale Aktion | ja |
| `action-workflows` | `overlay-workflows` | Alle Workflows | Verfügbare Workflows und Status | Workflow-Liste öffnen | Workflow-API oder lokale Aktion | ja |
| `sphere-container` | `overlay-sphere` | Hermes Sphäre | Zustand, Modus, Aktivität, Statusmeldungen | Zustandswechsel anzeigen | `/api/system`, Hermes-Status | nein |
| `chat-panel` | `overlay-chat` | Chat | Verlauf, letzte Eingaben, Antwortzeit | Chat öffnen, Verlauf ansehen | `/api/chat` | ja |
| `mic-btn` | `overlay-mic` | Spracheingabe | Aufnahmezustand, Erkennung, letzter Text | Mikrofon starten/stoppen | lokale Browser-Funktion | nein |
| `kbd-btn` | `overlay-keyboard` | Tastaturmodus | Eingabemodus, Fokus, Hinweise | Texteingabe aktivieren | keine | nein |
| `speech-btn` | `overlay-speech` | Sprachausgabe | TTS-Status, letzte Ausgabe, Lautstärke | Ausgabe sprechen/stoppen | `/api/tts` optional | nein |
| `panel-trading-center` | `overlay-trading-center` | Trading Center | Preis, Chart, Bid/Ask, Spread, Levels | Detailansicht, Symbolwechsel | spätere Trading-Read-API | nein |
| `panel-openrouter` | `overlay-openrouter` | Kosten & Guthaben | Verbrauch heute, Verbrauch Monat, Guthaben | Kosten-Detail, Usage-Ansicht | `/api/openrouter`, `/api/usage` | nein |
| `panel-hermes-agents` | `overlay-hermes-agents` | Hermes Agenten | Agentenliste, Laufstatus, Skills | Agentenstatus ansehen | `/api/hermes_status` | nein |
| `panel-quality-control` | `overlay-quality-control` | Quality Control | Prüfschritte, Freigaberate, Status | QC-Detail anzeigen | spätere QC-API | nein |
| `mod-publisher` | `overlay-publisher` | Publisher | Veröffentlichte Inhalte, Planung, nächste Publikation | Publisher öffnen | spätere Publish-API | ja |
| `mod-social` | `overlay-social` | Social Media | Plattformen, geplante Posts, Status | Social-Plan öffnen | spätere Social-API | ja |
| `mod-tasks` | `overlay-tasks` | Tasks | Offene, aktive und erledigte Aufgaben | Task-Board öffnen | spätere Task-API | ja |
| `mod-tradejournal` | `overlay-tradejournal` | Trade Journal | Trades, Trefferquote, Gewinn/Verlust | Journal öffnen | spätere Journal-API | ja |
| `mod-paperless` | `overlay-paperless` | Paperless | Dokumente, OCR-Queue, Status | Dokumentenansicht | spätere Paperless-API | ja |
| `mod-gbrain` | `overlay-gbrain` | GBrain | Quellen, Personen, Firmen, Konzepte | Wissensansicht öffnen | spätere Knowledge-API | ja |
| `mod-ai` | `overlay-ai-scout` | AI Scout | Gefundene Tools, Bewertung, Top-Fund | Scout-Übersicht öffnen | spätere Scout-API | ja |
| `mod-video` | `overlay-video-content` | Video Content | Shorts, Skripte, Produktion, Status | Video-Content öffnen | spätere Video-API | ja |

## Zusätzliche Vorgaben

- Trading im Overlay bleibt read-only.
- Hermes bleibt Agentensystem.
- Flask bleibt Anzeige- und API-Brücke.
- Keine Agentenlogik in Flask nachbauen.

