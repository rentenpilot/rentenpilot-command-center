# Dashboard Tiles Status

Interne Bestandsaufnahme der aktuellen Dashboard-Kacheln.

## Aktueller Stand

- Echt: Trading, Hermes-Status, Hermes-Agenten
- Statisch: Research, Content, Quality Control, untere Karten
- Klickbar: aktuell nur Trading-Symbole
- Ohne Endpoint: Research, Content, QC, Publisher, Social, Tasks, Trade Journal, Paperless, GBrain, AI Scout, Video Content
- Bekanntes Layoutproblem: Hermes-Agenten-Kachel überlappt nach unten, wird später behoben

## Kacheln

| Kachel | Status | Endpoint | Klickfunktion | Bekanntes Problem | Nächster sinnvoller Schritt |
|---|---|---|---|---|---|
| Research | statisch | keiner | nein | Hardcoded Werte in der UI | an echten Research-Status anbinden |
| Content | statisch | keiner | nein | Hardcoded Werte in der UI | an echten Content-Status anbinden |
| Trading | echt | `/api/trading/quotes`, `/api/trading/start_stream` | ja | keine aktuellen Funktionsprobleme bekannt | nur beobachten |
| Hermes-Status | echt | `/api/hermes_status` | nein | nur Statusanzeige, keine direkte Aktion | weiter als Health-Check nutzen |
| Hermes-Agenten | echt | `/api/hermes_status` | nein | Kachel überlappt nach unten | später inhaltlich/visuell vereinheitlichen |
| Quality Control | statisch | keiner | nein | Hardcoded OK-Werte | an echten QC-Endpoint anbinden |
| Publisher | statisch | keiner | nein | Platzhalterwerte | echten Publisher-Status ergänzen |
| Social Media | statisch | keiner | nein | Platzhalterwerte | echten Social-Status ergänzen |
| Tasks | statisch | keiner | nein | Platzhalterwerte | echten Task-Status ergänzen |
| Trade Journal | statisch | keiner | nein | Platzhalterwerte | echten Journal-Status ergänzen |
| Paperless | statisch | keiner | nein | Platzhalterwerte | echten Paperless-Status ergänzen |
| GBrain | statisch | keiner | nein | Platzhalterwerte | echten GBrain-Status ergänzen |
| AI Scout | statisch | keiner | nein | Platzhalterwerte | echten AI-Scout-Status ergänzen |
| Video Content | statisch | keiner | nein | Platzhalterwerte | echten Video-Status ergänzen |

## Hinweise

- Die Trading-Symbole sind aktuell die einzigen direkt klickbaren Elemente.
- `Hermes-Agenten` nutzt bereits echte Daten aus `/api/hermes_status`, bleibt aber layoutseitig zu hoch.
- Die untere Modulreihe ist derzeit weitgehend statisch und dient als Platzhalter für spätere Backend-Anbindung.
