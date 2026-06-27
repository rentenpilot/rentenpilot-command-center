# Dashboard Data Sources

Referenz: `reference/Hermes Dashboard.png`

## Leitregel
Dokumentiert werden aktuelle Datenquellen, geplante APIs, Dummy-Datenstatus und die Priorität der Anbindung. Flask bleibt Anzeige- und API-Brücke, nicht die Domänenlogik.

## Datenquelleninventar

| Modul | Aktuelle Datenquelle | Später geplante API | Dummy-Daten | Echte Daten | Priorität |
|---|---|---|---|---|---|
| `mod-research` | Dummy / statische UI-Werte | spätere Research-API oder Workflow-Daten | ja | später | hoch |
| `mod-content` | Dummy / statische UI-Werte | spätere Content-API oder Workflow-Daten | ja | später | hoch |
| `mod-trading` | Dummy / statische UI-Werte | spätere Trading-Read-API | ja | später | hoch |
| `action-research` | UI-Trigger | Workflow-Start ohne Backend-Logik in Flask | ja | später | mittel |
| `action-article` | UI-Trigger | Workflow-Start ohne Backend-Logik in Flask | ja | später | mittel |
| `action-seo` | UI-Trigger | Workflow-Start ohne Backend-Logik in Flask | ja | später | mittel |
| `action-trading-scan` | UI-Trigger | Workflow-Start ohne Backend-Logik in Flask | ja | später | mittel |
| `action-paperless-import` | UI-Trigger | Workflow-Start ohne Backend-Logik in Flask | ja | später | mittel |
| `action-workflows` | UI-Trigger | Workflow-Übersicht | ja | später | niedrig |
| `sphere-container` | Lokale Canvas-/Statuslogik | keine eigene API, Status aus Hermes/System | nein | teilweise | hoch |
| `chat-panel` | `/api/chat` | bleibt `/api/chat` | teils | ja | hoch |
| `mic-btn` | Browser SpeechRecognition | keine neue API | nein | ja, lokal | hoch |
| `kbd-btn` | UI-only | keine neue API | nein | nein | mittel |
| `speech-btn` | Browser SpeechSynthesis bzw. `/api/tts` falls vorhanden | keine neue API | nein | ja, lokal/optional | mittel |
| `panel-trading-center` | Dummy / statische Trading-Werte | `/api/trading/live?symbol=...` oder Read-only Feed | ja | später | hoch |
| `panel-openrouter` | `/api/openrouter` und `/api/usage` | bleibt OpenRouter / Usage-Brücke | nein | ja | hoch |
| `panel-hermes-agents` | `/api/hermes_status` | Hermes Agenten / Skills / Workflows | nein | ja | hoch |
| `panel-quality-control` | Dummy / UI-Status | spätere QC-API oder lokale Auswertung | ja | später | hoch |
| `mod-publisher` | Dummy | spätere Publish-/Content-API | ja | später | mittel |
| `mod-social` | Dummy | spätere Social-API | ja | später | mittel |
| `mod-tasks` | Dummy | spätere Task-API | ja | später | mittel |
| `mod-tradejournal` | Dummy | spätere Journal-API | ja | später | mittel |
| `mod-paperless` | Dummy | spätere Paperless-API | ja | später | mittel |
| `mod-gbrain` | Dummy | spätere Knowledge-API | ja | später | mittel |
| `mod-ai` | Dummy | spätere Scout-/Discovery-API | ja | später | mittel |
| `mod-video` | Dummy | spätere Video-Content-API | ja | später | mittel |

