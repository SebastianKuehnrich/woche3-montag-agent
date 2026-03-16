# Autonomer Agent mit Tool Use

Ein interaktiver CLI-Agent auf Basis der Anthropic Claude API mit autonomem Tool-Use-Loop.

## Features

- **5 Tools:** Rechner, Aktuelles Datum, Text-Analyse, Einheiten-Umrechner, Web-Suche (DuckDuckGo)
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
```

## Tiers

| Tier | Features |
|------|----------|
| **Bronze** | 3 Tools + Agent Loop |
| **Silver** | 4. Tool + Conversation History |
| **Gold** | Structured Output + Error Handling |
| **Platinum** | Web-Suche (DuckDuckGo) |
