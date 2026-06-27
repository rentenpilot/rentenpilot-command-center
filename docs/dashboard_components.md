# Dashboard Components

Referenz: `reference/Hermes Dashboard.png`

## Leitregel
Eine sichtbare Kachel entspricht genau einem eigenen Klickbereich. Keine Gruppen-Hotspots, keine Reihen-Hotspots, keine unsichtbaren Overlay-Flächen.

## Komponenteninventar

| ID | Sichtbarer Name | Position im Dashboard | Zweck | Unterelemente | Klickbar | Eigener Hit-Bereich | Overlay | Priorität |
|---|---|---|---|---|---|---|---|---|
| `mod-research` | Research | Linke Spalte, Hauptmodule | Themenrecherche und Quellenüberblick | Icon, Status, Kennzahlen, Pfeil | ja | ja | ja | hoch |
| `mod-content` | Content | Linke Spalte, Hauptmodule | Content-Planung und Bearbeitungsstatus | Icon, Status, Kennzahlen, Pfeil | ja | ja | ja | hoch |
| `mod-trading` | Trading | Linke Spalte, Hauptmodule | Trading-Signale und Auswertung | Icon, Status, Kennzahlen, Pfeil | ja | ja | ja | hoch |
| `action-research` | Recherche starten | Linke Spalte, Schnellaktionen | Schneller Einstieg in Recherche-Workflow | Button-Text, Icon | ja | ja | nein | mittel |
| `action-article` | Artikel erstellen | Linke Spalte, Schnellaktionen | Content-Erstellung anstoßen | Button-Text, Icon | ja | ja | nein | mittel |
| `action-seo` | SEO Analyse | Linke Spalte, Schnellaktionen | SEO-Analyse starten | Button-Text, Icon | ja | ja | nein | mittel |
| `action-trading-scan` | Trading Scan | Linke Spalte, Schnellaktionen | Trading-Scan öffnen | Button-Text, Icon | ja | ja | nein | mittel |
| `action-paperless-import` | Paperless Import | Linke Spalte, Schnellaktionen | Dokumentenimport starten | Button-Text, Icon | ja | ja | nein | mittel |
| `action-workflows` | Alle Workflows anzeigen | Linke Spalte, Schnellaktionen | Übersicht aller Workflows | Link-Text | ja | ja | nein | niedrig |
| `sphere-container` | Hermes Sphäre | Mitte oben | Visuelle Hermes-Zentrale, Status und Zustand | Canvas, Ringe, Logo, Statustext | ja | ja | ja | hoch |
| `chat-panel` | Chatbereich | Mitte unten | Chat mit Hermes | Verlauf, Eingabebereich, Steuerung | ja | ja | ja | hoch |
| `mic-btn` | Spracheingabe | Mitte unten | Spracherkennung starten/stoppen | Icon, Text | ja | ja | ja | hoch |
| `kbd-btn` | Tastaturmodus | Mitte unten | Texteingabe aktivieren | Icon, Text | ja | ja | ja | mittel |
| `speech-btn` | Sprachausgabe | Mitte unten | Sprachwiedergabe umschalten | Icon, Text | ja | ja | ja | mittel |
| `panel-trading-center` | Trading Center | Rechte Spalte oben | Marktübersicht, Signal, Kurs, Chart | Titel, Status, Asset-Tabs, Preis, Chart, Levels | ja | ja | ja | hoch |
| `panel-openrouter` | Kosten & Guthaben / OpenRouter | Rechte Spalte Mitte | Kosten- und Guthabenanzeige | Titel, 3 Werte | ja | ja | ja | hoch |
| `panel-hermes-agents` | Hermes Agenten | Rechte Spalte unten links | Agentenstatus und Laufzustände | Liste, Statusfarben | ja | ja | ja | hoch |
| `panel-quality-control` | Quality Control | Rechte Spalte unten rechts | Freigabe- und Prüfstatus | Prüfliste, Freigaberate | ja | ja | ja | hoch |
| `mod-publisher` | Publisher | Untere Modulreihe | Veröffentlichungsstatus | Kennzahlen | ja | ja | ja | mittel |
| `mod-social` | Social Media | Untere Modulreihe | Social-Planung und Plattformstatus | Kennzahlen | ja | ja | ja | mittel |
| `mod-tasks` | Tasks | Untere Modulreihe | Aufgabenstatus | Kennzahlen | ja | ja | ja | mittel |
| `mod-tradejournal` | Trade Journal | Untere Modulreihe | Handelsverlauf und Trefferquote | Kennzahlen | ja | ja | ja | mittel |
| `mod-paperless` | Paperless | Untere Modulreihe | Dokumentenbestand und OCR-Queue | Kennzahlen | ja | ja | ja | mittel |
| `mod-gbrain` | GBrain | Untere Modulreihe | Wissensbasis und Ressourcen | Kennzahlen | ja | ja | ja | mittel |
| `mod-ai` | AI Scout | Untere Modulreihe | Tool-Scouting | Kennzahlen | ja | ja | ja | mittel |
| `mod-video` | Video Content | Untere Modulreihe | Video-Content-Überblick | Kennzahlen | ja | ja | ja | mittel |

