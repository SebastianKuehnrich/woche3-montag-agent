# Autonomer Agent mit Tool Use

Ein interaktiver CLI-Agent auf Basis der Anthropic Claude API mit autonomem Tool-Use-Loop.

## Features

- **7 Tools:** Rechner, Aktuelles Datum, Text-Analyse, Einheiten-Umrechner, Web-Suche, Datei-Tool, Notizen
- **Agent Loop:** Autonome Tool-Auswahl und -Verkettung (Claude entscheidet selbst welche Tools er braucht)
- **Conversation History:** Gedaechtnis ueber mehrere Fragen hinweg
- **Structured Output:** Erzwungenes JSON-Schema via `tool_choice`
- **Defensive Coding:** Input-Validierung, sichere Auswertung (kein `eval`), granulares Error Handling

## Voraussetzungen

- Python 3.10+
- Anthropic API Key

## Installation

```bash
pip install anthropic python-dotenv duckduckgo_search
```

`.env` Datei erstellen (siehe `.env.example`):

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

## Starten

```bash
python main.py
```

## Befehle im Agent

| Befehl | Beschreibung |
|--------|-------------|
| `quit` | Agent beenden |
| `history` | Conversation History anzeigen |
| `clear` | History loeschen |
| `analyse: <text>` | Structured Output (Gold) |

## Tools im Detail

| Tool | Beschreibung | Beispiel-Prompt |
|------|-------------|-----------------|
| `rechner` | Sichere mathematische Berechnungen (kein `eval`) | "Was ist 42 * 17 + 891?" |
| `aktuelles_datum` | Datum, Uhrzeit und Wochentag | "Welcher Tag ist heute?" |
| `text_analyse` | Wortanzahl, Satzanzahl, Top-5 Woerter | "Analysiere diesen Text: ..." |
| `einheiten_umrechner` | Temperatur, Distanz, Gewicht | "Rechne 100 km in Meilen um" |
| `web_suche` | DuckDuckGo Internet-Suche (live) | "Suche nach aktuellen KI-Nachrichten" |
| `datei_tool` | Lokale Dateien lesen/schreiben | "Lies die Datei reflexion.md" |
| `notizen` | Persistente Notizen (speichern/lesen/loeschen) | "Merke dir: Meeting morgen 14 Uhr" |

## Defensive Coding Massnahmen

- **Kein unsicheres `eval()`** — `compile()` mit leerem `__builtins__` Namespace
- **Path Traversal Schutz** — Datei-Tool erlaubt nur Dateien im Projektverzeichnis
- **Input-Validierung** — Alle Tool-Inputs werden auf Typ, Laenge und erlaubte Werte geprueft
- **Granulares Error Handling** — Jeder API-Fehler (401, 429, 500) wird separat behandelt
- **Crashsicherer Betrieb** — `tool_ausfuehren_sicher()` faengt alle Exceptions ab
- **Max Loop-Iterationen** — Schutz gegen Endlosschleifen (max 10 Durchlaeufe)
- **JSON-Korruptionsschutz** — Notizen-Datei wird bei Fehler neu erstellt

## Architektur

```
User Input
    |
    v
Agent Loop (max 10 Durchlaeufe)
    |
    v
Claude API (mit Tool-Definitionen)
    |
    +-- stop_reason: "end_turn"  --> Finale Antwort
    |
    +-- stop_reason: "tool_use" --> Tool lokal ausfuehren
            |                       Ergebnis zurueck an Claude
            +-- rechner             (sichere Berechnung)
            +-- aktuelles_datum     (Datum/Uhrzeit)
            +-- text_analyse        (Wortanzahl, Top-5 etc.)
            +-- einheiten_umrechner (Temperatur, Distanz, Gewicht)
            +-- web_suche           (DuckDuckGo Internet-Suche)
            +-- datei_tool          (Dateien lesen/schreiben)
            +-- notizen             (persistente Notizen speichern/laden)
```

## Projektstruktur

```
woche3-montag-agent/
    agent.py              # Hauptmodul: Tools, Agent Loop, Structured Output
    main.py               # Einstiegspunkt (startet agent.py)
    test_connection.py    # API-Verbindungstest
    verstaendnisfragen.py # Verstaendnisfragen zum Kurs
    reflexion.md          # Reflexion ueber das Projekt
    .env.example          # Vorlage fuer API Key
    .gitignore            # Git-Ausschluesse
```

## Tiers

| Tier | Features |
|------|----------|
| **Bronze** | 3 Tools + Agent Loop |
| **Silver** | 4. Tool + Conversation History |
| **Gold** | Structured Output + Error Handling |
| **Platinum** | Web-Suche, Datei-Tool, Notizen |
