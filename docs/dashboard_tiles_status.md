# Dashboard Tiles Status

Interne Bestandsaufnahme der aktuellen Dashboard-Kacheln.

## Aktueller Stand

- Echt: Trading, Hermes-Status, Hermes-Agenten
- An Backend angebunden: Research, Content, Quality, Publisher, Social, Tasks, Trade Journal, Paperless, GBrain, AI Scout, Video
- Aktueller Fallback-Status: `not_implemented`, wenn der passende Backend-Agent noch fehlt
- Keine Dummy-Werte mehr in den angebundenen Kacheln
- Klickbar: aktuell nur Trading-Symbole
- Bekanntes Layoutproblem: Hermes-Agenten-Kachel überlappt nach unten, wird später behoben

## Kacheln

| Kachel | Status | Endpoint | Klickfunktion | Bekanntes Problem | Nächster sinnvoller Schritt |
|---|---|---|---|---|---|
| Research | angebunden | `/api/research/status` | nein | Backend liefert aktuell `not_implemented` | später echten Research-Agent anbinden |
| Content | angebunden | `/api/content/status` | nein | Backend liefert aktuell `not_implemented` | später echten Content-Agent anbinden |
| Trading | echt | `/api/trading/quotes`, `/api/trading/start_stream` | ja | keine aktuellen Funktionsprobleme bekannt | nur beobachten |
| Hermes-Status | echt | `/api/hermes_status` | nein | nur Statusanzeige, keine direkte Aktion | weiter als Health-Check nutzen |
| Hermes-Agenten | echt | `/api/hermes_status` | nein | Kachel überlappt nach unten | später inhaltlich/visuell vereinheitlichen |
| Quality Control | angebunden | `/api/quality/status` | nein | Backend liefert aktuell `not_implemented` | später echten QC-Review-Loop anbinden |
| Publisher | angebunden | `/api/publisher/status` | nein | Backend liefert aktuell `not_implemented` | später echten Publisher-Agenten anbinden |
| Social Media | angebunden | `/api/social/status` | nein | Backend liefert aktuell `not_implemented` | später echten Social-Agenten anbinden |
| Tasks | angebunden | `/api/tasks/status` | nein | Backend liefert aktuell `not_implemented` | später echtes Task-System anbinden |
| Trade Journal | angebunden | `/api/trade-journal/status` | nein | Backend liefert aktuell `not_implemented` | später echtes Journal-Modul anbinden |
| Paperless | angebunden | `/api/paperless/status` | nein | Backend liefert aktuell `not_implemented` | später echte Paperless-Anbindung ergänzen |
| GBrain | angebunden | `/api/gbrain/status` | nein | Backend liefert aktuell `not_implemented` | später echtes GBrain-Backend anbinden |
| AI Scout | angebunden | `/api/ai-scout/status` | nein | Backend liefert aktuell `not_implemented` | später echten AI-Scout-Agenten anbinden |
| Video Content | angebunden | `/api/video/status` | nein | Backend liefert aktuell `not_implemented` | später echten Video-Agenten anbinden |

## Hinweise

- Die Trading-Symbole sind aktuell die einzigen direkt klickbaren Elemente.
- `Hermes-Agenten` nutzt bereits echte Daten aus `/api/hermes_status`, bleibt aber layoutseitig zu hoch.
- Die untere Modulreihe ist jetzt technisch angebunden, liefert aber noch `not_implemented`, bis die jeweiligen Backend-Agenten existieren.
