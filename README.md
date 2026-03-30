# Autonomer Agent mit Tool Use + Multi-Agent System

Zwei Systeme auf Basis der Anthropic Claude API:

1. **Single Agent** — Interaktiver CLI-Agent mit 7 Tools und autonomem Tool-Use-Loop
2. **Multi-Agent System** — Supervisor-Worker Pattern mit 3 spezialisierten Agents

## Single Agent (`agent.py`)

### Features

- **7 Tools:** Rechner, Aktuelles Datum, Text-Analyse, Einheiten-Umrechner, Web-Suche, Datei-Tool, Notizen
- **Agent Loop:** Autonome Tool-Auswahl und -Verkettung (Claude entscheidet selbst welche Tools er braucht)
- **Conversation History:** Gedaechtnis ueber mehrere Fragen hinweg
- **Structured Output:** Erzwungenes JSON-Schema via `tool_choice`
- **Defensive Coding:** Input-Validierung, sichere Auswertung (kein `eval`), granulares Error Handling

### Starten

```bash
python main.py
```

### Befehle

| Befehl | Beschreibung |
|--------|-------------|
| `quit` | Agent beenden |
| `history` | Conversation History anzeigen |
| `clear` | History loeschen |
| `analyse: <text>` | Structured Output (Gold) |

### Tools

| Tool | Beschreibung | Beispiel |
|------|-------------|----------|
| `rechner` | Sichere mathematische Berechnungen | "Was ist 42 * 17 + 891?" |
| `aktuelles_datum` | Datum, Uhrzeit und Wochentag | "Welcher Tag ist heute?" |
| `text_analyse` | Wortanzahl, Satzanzahl, Top-5 Woerter | "Analysiere diesen Text: ..." |
| `einheiten_umrechner` | Temperatur, Distanz, Gewicht | "Rechne 100 km in Meilen um" |
| `web_suche` | DuckDuckGo Internet-Suche | "Suche nach aktuellen KI-News" |
| `datei_tool` | Lokale Dateien lesen/schreiben | "Lies die Datei reflexion.md" |
| `notizen` | Persistente Notizen speichern/lesen | "Merke dir: Meeting morgen 14 Uhr" |

## Multi-Agent System (`multi_agent_system/`)

### Architektur: Supervisor-Worker Pattern

```
User Anfrage
    |
    v
+---------------------+
|     SUPERVISOR       |  Routet an den richtigen Agent
+---------------------+
    |         |         |
    v         v         v
+--------+ +--------+ +--------+
|Research| |Analysis| | Writer |
| Agent  | | Agent  | | Agent  |
+--------+ +--------+ +--------+
| web_   | | text_  | |markdown|
| suche  | |analyse | |_format |
| zusamm-| |sentiment| |report_ |
| fassung| |vergleich| |erstellen|
+--------+ +--------+ +--------+
```

### Agents

| Agent | Tools | Aufgabe |
|-------|-------|---------|
| **Research Agent** | `web_suche`, `zusammenfassung` | Internet-Recherche und Zusammenfassung |
| **Analysis Agent** | `text_analyse`, `sentiment_analyse`, `text_vergleich` | Textanalyse und Sentiment-Erkennung |
| **Writer Agent** | `markdown_formatierung`, `report_erstellen` | Reports und Markdown-Dokumente erstellen |

### Features

- **Supervisor Routing:** Claude entscheidet automatisch welcher Agent zustaendig ist
- **Agent Chaining:** Ergebnisse von einem Agent fliessen in den naechsten
- **Context Isolation:** Jeder Agent hat eigene Messages und Tools
- **Token Tracking:** Verbrauch pro Agent und gesamt
- **Error Handling + Retry:** Fehlgeschlagene Agents werden automatisch wiederholt

### Starten

```bash
python -m multi_agent_system.main
```

### Befehle

| Befehl | Beschreibung |
|--------|-------------|
| `quit` | System beenden |
| `tokens` | Token-Verbrauch pro Agent anzeigen |

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

## Defensive Coding

- **Kein unsicheres `eval()`** — `compile()` mit leerem `__builtins__` Namespace
- **Path Traversal Schutz** — Datei-Tool erlaubt nur Dateien im Projektverzeichnis
- **Input-Validierung** — Alle Tool-Inputs werden auf Typ, Laenge und erlaubte Werte geprueft
- **Granulares Error Handling** — Jeder API-Fehler (401, 429, 500) wird separat behandelt
- **Crashsicherer Betrieb** — `tool_ausfuehren_sicher()` faengt alle Exceptions ab
- **Max Loop-Iterationen** — Schutz gegen Endlosschleifen
- **Context Isolation** — Agents koennen sich nicht gegenseitig beeinflussen

## Projektstruktur

```
woche3-montag-agent/
    agent.py                          # Single Agent (7 Tools, Agent Loop)
    main.py                           # Einstiegspunkt Single Agent
    test_connection.py                # API-Verbindungstest
    verstaendnisfragen.py             # Verstaendnisfragen zum Kurs
    reflexion.md                      # Reflexion ueber das Projekt
    .env.example                      # Vorlage fuer API Key
    multi_agent_system/
        main.py                       # Supervisor (routet an Agents)
        config.py                     # Shared Settings
        agents/
            research_agent.py         # Web-Suche + Zusammenfassung
            analysis_agent.py         # Text-Analyse + Sentiment
            writer_agent.py           # Markdown + Reports
        tools/
            research_tools.py         # Research Tool-Implementierungen
            analysis_tools.py         # Analysis Tool-Implementierungen
            writer_tools.py           # Writer Tool-Implementierungen
        utils/
            context_manager.py        # Context Isolation
            token_tracker.py          # Token-Verbrauch Tracking
            safe_print.py             # Windows-safe Print (Unicode)
```

## Tiers

| Tier | Single Agent | Multi-Agent System |
|------|-------------|-------------------|
| **Bronze** | 3 Tools + Agent Loop | Supervisor + 2 Agents |
| **Silver** | 4. Tool + History | 3. Agent + Chaining |
| **Gold** | Structured Output + Error Handling | Retry + Token Tracking |
| **Platinum** | Web-Suche, Datei-Tool, Notizen | Context Management |
