"""
agent.py — Autonomer Agent mit Tool Use Loop (Bronze + Silver + Gold).

Implementiert das Anthropic Agent Pattern 6: Autonomous Agent
    User -> LLM -> "Ich brauche Tool X" -> Tool ausfuehren -> Ergebnis -> LLM -> ...

Tiers:
    BRONZE: 3 Tools (rechner, aktuelles_datum, text_analyse) + Agent Loop
    SILVER: 4. Tool (einheiten_umrechner) + Conversation History
    GOLD:   Structured Output (tool_choice) + Error Handling

Defensive Coding:
    - Kein unsicheres eval() — stattdessen compile() mit leerem __builtins__
    - Alle API-Calls mit granularem Exception Handling
    - Input-Validierung fuer alle Tool-Inputs
    - Maximale Loop-Iterationen als Schutz gegen Endlosschleifen
    - Type Checks auf API-Responses
    - Tool-Ausfuehrung in try/except-Wrapper (Gold: tool_ausfuehren_sicher)

Datum: 17.03.2026 | Sebastian
"""

import json
import logging
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ─── Dependency Checks (Defensive: Fehlende Pakete abfangen) ────────────────

try:
    import anthropic
except ImportError:
    print("FEHLER: 'anthropic' nicht installiert. -> pip install anthropic")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("FEHLER: 'python-dotenv' nicht installiert. -> pip install python-dotenv")
    sys.exit(1)

try:
    from duckduckgo_search import DDGS
except ImportError:
    print("FEHLER: 'duckduckgo_search' nicht installiert. -> pip install duckduckgo_search")
    sys.exit(1)


# ─── Logging Setup ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Konfiguration ──────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024
MAX_LOOP_ITERATIONS = 10  # Schutz gegen Endlosschleifen
SYSTEM_PROMPT = (
    "Du bist ein hilfreicher Assistent mit Gedaechtnis. "
    "Du erinnerst dich an vorherige Nachrichten in diesem Gespraech. "
    "Du hast Zugriff auf Tools und nutzt sie wenn noetig. "
    "Antworte immer auf Deutsch. "
    "Wenn du ein Tool brauchst, benutze es — rate nicht."
)


# ══════════════════════════════════════════════════════════════════════════════
# BRONZE: Tool-Definitionen (JSON Schema fuer Anthropic API)
# ══════════════════════════════════════════════════════════════════════════════
#
# Jedes Tool hat: name, description, input_schema
# WICHTIG: Die description ist ENTSCHEIDEND — Claude liest NUR die
# description um zu entscheiden ob er das Tool braucht.

TOOLS: list[dict[str, Any]] = [
    {
        "name": "rechner",
        "description": (
            "Berechnet mathematische Ausdruecke. Verwende dieses Tool fuer "
            "ALLE Berechnungen — Addition, Subtraktion, Multiplikation, Division, "
            "Prozentrechnung, Potenzen. Verwende es NICHT fuer Schaetzungen oder "
            "Approximationen, sondern nur fuer exakte Berechnungen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ausdruck": {
                    "type": "string",
                    "description": (
                        "Der mathematische Ausdruck, z.B. '(42 * 17) + 891' "
                        "oder '2**10' oder 'sqrt(144)'"
                    ),
                }
            },
            "required": ["ausdruck"],
        },
    },
    {
        "name": "aktuelles_datum",
        "description": (
            "Gibt das aktuelle Datum, die Uhrzeit und den Wochentag zurueck. "
            "Verwende dieses Tool wenn nach dem heutigen Datum, der aktuellen "
            "Uhrzeit, dem Wochentag, oder zeitbezogenen Informationen gefragt wird."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "text_analyse",
        "description": (
            "Analysiert einen Text und gibt detaillierte Statistiken zurueck: "
            "Wortanzahl, Zeichenanzahl, Satzanzahl, durchschnittliche Wortlaenge, "
            "und die 5 haeufigsten Woerter. Verwende dieses Tool wenn jemand einen "
            "Text analysieren, zaehlen oder statistisch auswerten lassen will."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Der Text der analysiert werden soll",
                }
            },
            "required": ["text"],
        },
    },
    # ══════════════════════════════════════════════════════════════════════════
    # PLATINUM: 5. Tool — Web-Suche (DuckDuckGo)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "name": "web_suche",
        "description": (
            "Sucht im Internet nach aktuellen Informationen. Verwende dieses Tool "
            "wenn nach aktuellen Nachrichten, Fakten, Personen, Ereignissen oder "
            "anderen Informationen gefragt wird, die du nicht sicher weisst. "
            "Verwende es NICHT fuer Berechnungen oder Einheiten-Umrechnungen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "suchbegriff": {
                    "type": "string",
                    "description": "Der Suchbegriff, z.B. 'aktuelle Nachrichten KI 2026'",
                },
                "max_ergebnisse": {
                    "type": "integer",
                    "description": "Maximale Anzahl Ergebnisse (1-5, Standard: 3)",
                },
            },
            "required": ["suchbegriff"],
        },
    },
    # ══════════════════════════════════════════════════════════════════════════
    # SILVER: 4. eigenes Tool — Einheiten-Umrechner
    # ══════════════════════════════════════════════════════════════════════════
    {
        "name": "einheiten_umrechner",
        "description": (
            "Rechnet physikalische Einheiten um: Temperatur (Celsius/Fahrenheit), "
            "Distanz (km/miles, meter/feet), Gewicht (kg/lbs). "
            "Verwende dieses Tool fuer alle Einheiten-Umrechnungen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "wert": {
                    "type": "number",
                    "description": "Der Zahlenwert zum Umrechnen",
                },
                "von": {
                    "type": "string",
                    "description": (
                        "Ausgangseinheit, z.B. 'celsius', 'km', 'kg', 'meter'"
                    ),
                },
                "nach": {
                    "type": "string",
                    "description": (
                        "Zieleinheit, z.B. 'fahrenheit', 'miles', 'lbs', 'feet'"
                    ),
                },
            },
            "required": ["wert", "von", "nach"],
        },
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# GOLD: Structured Output Tool (fuer tool_choice Erzwingung)
# ══════════════════════════════════════════════════════════════════════════════

ANALYSE_OUTPUT_TOOL: dict[str, Any] = {
    "name": "analyse_ergebnis",
    "description": "Strukturiertes Ergebnis einer Analyse",
    "input_schema": {
        "type": "object",
        "properties": {
            "zusammenfassung": {
                "type": "string",
                "description": "Kurze Zusammenfassung in 1-2 Saetzen",
            },
            "stichpunkte": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 wichtige Punkte",
            },
            "bewertung": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": "Bewertung der Textqualitaet 1-10",
            },
        },
        "required": ["zusammenfassung", "stichpunkte", "bewertung"],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# Tool-Implementierungen (laufen LOKAL — Claude hat keinen Zugriff)
# ══════════════════════════════════════════════════════════════════════════════


def tool_rechner(ausdruck: str) -> str:
    """Berechnet einen mathematischen Ausdruck SICHER (kein unsicheres eval).

    Erlaubte Operationen: Grundrechenarten, Potenz, sqrt, sin, cos, tan, pi, e.
    Alles andere wird abgelehnt.
    """
    # Defensive: Input-Validierung
    if not isinstance(ausdruck, str) or not ausdruck.strip():
        return json.dumps({"fehler": "Leerer Ausdruck."}, ensure_ascii=False)

    if len(ausdruck) > 500:
        return json.dumps(
            {"fehler": "Ausdruck zu lang (max 500 Zeichen)."},
            ensure_ascii=False,
        )

    # Erlaubte Zeichen und Funktionen
    erlaubt = set("0123456789+-*/.() ")
    erlaubte_woerter = {"sqrt", "sin", "cos", "tan", "pi", "e", "abs", "log"}

    # Pruefe ob nur erlaubte Zeichen enthalten sind
    bereinigt = ausdruck.strip()
    for wort in erlaubte_woerter:
        bereinigt = bereinigt.replace(wort, "")

    unerlaubt = set(bereinigt) - erlaubt
    if unerlaubt:
        return json.dumps(
            {"fehler": f"Unerlaubte Zeichen: {unerlaubt}"},
            ensure_ascii=False,
        )

    # Sichere Auswertung mit eingeschraenktem Namespace
    safe_namespace: dict[str, Any] = {
        "__builtins__": {},  # KEINE Builtins = kein os, sys, import etc.
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "abs": abs,
        "log": math.log,
        "pi": math.pi,
        "e": math.e,
    }

    try:
        code = compile(ausdruck, "<rechner>", "eval")

        # Zusaetzliche Sicherheit: Pruefe Bytecode auf verbotene Funktionen
        for name in code.co_names:
            if name not in safe_namespace:
                return json.dumps(
                    {"fehler": f"Unbekannte Funktion '{name}'."},
                    ensure_ascii=False,
                )

        ergebnis = eval(code, safe_namespace)
        return json.dumps(
            {"ausdruck": ausdruck, "ergebnis": ergebnis},
            ensure_ascii=False,
        )
    except ZeroDivisionError:
        return json.dumps({"fehler": "Division durch Null."}, ensure_ascii=False)
    except (ValueError, TypeError, OverflowError) as exc:
        return json.dumps(
            {"fehler": f"Berechnung fehlgeschlagen: {exc}"},
            ensure_ascii=False,
        )
    except SyntaxError:
        return json.dumps(
            {"fehler": f"Ungueltige Syntax: '{ausdruck}'"},
            ensure_ascii=False,
        )


def tool_aktuelles_datum() -> str:
    """Gibt das aktuelle Datum, Uhrzeit und Wochentag zurueck."""
    jetzt = datetime.now()

    # Deutsche Wochentage (locale-unabhaengig)
    wochentage = {
        "Monday": "Montag",
        "Tuesday": "Dienstag",
        "Wednesday": "Mittwoch",
        "Thursday": "Donnerstag",
        "Friday": "Freitag",
        "Saturday": "Samstag",
        "Sunday": "Sonntag",
    }
    wochentag_en = jetzt.strftime("%A")
    wochentag_de = wochentage.get(wochentag_en, wochentag_en)

    return json.dumps(
        {
            "datum": jetzt.strftime("%d.%m.%Y"),
            "uhrzeit": jetzt.strftime("%H:%M:%S"),
            "wochentag": wochentag_de,
            "iso": jetzt.isoformat(),
        },
        ensure_ascii=False,
    )


def tool_text_analyse(text: str) -> str:
    """Analysiert einen Text und gibt detaillierte Statistiken zurueck."""
    # Defensive: Input-Validierung
    if not isinstance(text, str) or not text.strip():
        return json.dumps({"fehler": "Leerer Text."}, ensure_ascii=False)

    if len(text) > 50000:
        return json.dumps(
            {"fehler": "Text zu lang (max 50.000 Zeichen)."},
            ensure_ascii=False,
        )

    woerter = text.split()
    saetze = text.count(".") + text.count("!") + text.count("?")
    zeichen = len(text)
    avg_wortlaenge = (
        sum(len(w) for w in woerter) / len(woerter) if woerter else 0
    )

    # Haeufigste Woerter zaehlen
    zaehlung: dict[str, int] = {}
    for wort in woerter:
        clean = wort.lower().strip(".,!?;:()[]\"'")
        if len(clean) > 2:  # Nur Woerter mit mehr als 2 Buchstaben
            zaehlung[clean] = zaehlung.get(clean, 0) + 1
    top_5 = sorted(zaehlung.items(), key=lambda x: x[1], reverse=True)[:5]

    return json.dumps(
        {
            "wortanzahl": len(woerter),
            "zeichenanzahl": zeichen,
            "satzanzahl": saetze,
            "durchschnittliche_wortlaenge": round(avg_wortlaenge, 1),
            "top_5_woerter": [{"wort": w, "anzahl": c} for w, c in top_5],
        },
        ensure_ascii=False,
    )


def tool_einheiten_umrechner(wert: float, von: str, nach: str) -> str:
    """Rechnet physikalische Einheiten um (SILVER Tool).

    Unterstuetzt: Temperatur, Distanz, Gewicht.
    """
    # Defensive: Input-Validierung
    if not isinstance(wert, (int, float)):
        return json.dumps(
            {"fehler": "Wert muss eine Zahl sein."},
            ensure_ascii=False,
        )

    von = von.lower().strip()
    nach = nach.lower().strip()

    umrechnungen: dict[tuple[str, str], Any] = {
        ("celsius", "fahrenheit"): lambda x: x * 9 / 5 + 32,
        ("fahrenheit", "celsius"): lambda x: (x - 32) * 5 / 9,
        ("km", "miles"): lambda x: x * 0.621371,
        ("miles", "km"): lambda x: x * 1.60934,
        ("kg", "lbs"): lambda x: x * 2.20462,
        ("lbs", "kg"): lambda x: x * 0.453592,
        ("meter", "feet"): lambda x: x * 3.28084,
        ("feet", "meter"): lambda x: x * 0.3048,
        ("meter", "fuss"): lambda x: x * 3.28084,
        ("fuss", "meter"): lambda x: x * 0.3048,
    }

    key = (von, nach)
    if key in umrechnungen:
        ergebnis = umrechnungen[key](wert)
        return json.dumps(
            {
                "original": f"{wert} {von}",
                "umgerechnet": f"{round(ergebnis, 4)} {nach}",
            },
            ensure_ascii=False,
        )

    verfuegbar = [f"{v} -> {n}" for v, n in umrechnungen]
    return json.dumps(
        {
            "fehler": f"Umrechnung {von} -> {nach} nicht unterstuetzt.",
            "verfuegbare_umrechnungen": verfuegbar,
        },
        ensure_ascii=False,
    )


def tool_web_suche(suchbegriff: str, max_ergebnisse: int = 3) -> str:
    """Sucht im Internet via DuckDuckGo (PLATINUM Tool).

    Defensive Massnahmen:
        - Input-Validierung (leerer String, Laenge)
        - max_ergebnisse auf 1-5 begrenzt
        - Timeout-Handling
        - Exception-Handling fuer Netzwerkfehler
    """
    # Defensive: Input-Validierung
    if not isinstance(suchbegriff, str) or not suchbegriff.strip():
        return json.dumps({"fehler": "Leerer Suchbegriff."}, ensure_ascii=False)

    if len(suchbegriff) > 200:
        return json.dumps(
            {"fehler": "Suchbegriff zu lang (max 200 Zeichen)."},
            ensure_ascii=False,
        )

    # Defensive: max_ergebnisse begrenzen
    if not isinstance(max_ergebnisse, int) or max_ergebnisse < 1:
        max_ergebnisse = 3
    max_ergebnisse = min(max_ergebnisse, 5)

    try:
        with DDGS() as ddgs:
            resultate = list(ddgs.text(suchbegriff, max_results=max_ergebnisse))

        if not resultate:
            return json.dumps(
                {"suchbegriff": suchbegriff, "ergebnisse": [], "hinweis": "Keine Ergebnisse gefunden."},
                ensure_ascii=False,
            )

        ergebnisse = []
        for r in resultate:
            ergebnisse.append({
                "titel": r.get("title", ""),
                "link": r.get("href", ""),
                "beschreibung": r.get("body", ""),
            })

        return json.dumps(
            {"suchbegriff": suchbegriff, "anzahl": len(ergebnisse), "ergebnisse": ergebnisse},
            ensure_ascii=False,
        )

    except Exception as exc:
        logger.error("Web-Suche fehlgeschlagen: %s", exc)
        return json.dumps(
            {"fehler": f"Web-Suche fehlgeschlagen: {exc}"},
            ensure_ascii=False,
        )


# ─── Tool-Registry (Mapping Name → Funktion) ────────────────────────────────

TOOL_REGISTRY: dict[str, Any] = {
    "rechner": lambda inputs: tool_rechner(inputs.get("ausdruck", "")),
    "aktuelles_datum": lambda inputs: tool_aktuelles_datum(),
    "text_analyse": lambda inputs: tool_text_analyse(inputs.get("text", "")),
    "einheiten_umrechner": lambda inputs: tool_einheiten_umrechner(
        inputs.get("wert", 0),
        inputs.get("von", ""),
        inputs.get("nach", ""),
    ),
    "web_suche": lambda inputs: tool_web_suche(
        inputs.get("suchbegriff", ""),
        inputs.get("max_ergebnisse", 3),
    ),
}


# ══════════════════════════════════════════════════════════════════════════════
# GOLD: Sichere Tool-Ausfuehrung mit Error Handling
# ══════════════════════════════════════════════════════════════════════════════


def tool_ausfuehren(name: str, eingabe: dict) -> str:
    """Fuehrt ein Tool lokal aus (ohne Error-Wrapper)."""
    if name not in TOOL_REGISTRY:
        return json.dumps(
            {"fehler": f"Unbekanntes Tool: {name}"},
            ensure_ascii=False,
        )

    if not isinstance(eingabe, dict):
        return json.dumps(
            {"fehler": "Tool-Input muss ein Dictionary sein."},
            ensure_ascii=False,
        )

    return TOOL_REGISTRY[name](eingabe)


def tool_ausfuehren_sicher(name: str, eingabe: dict) -> str:
    """GOLD: Wrapper mit Error Handling — Agent crasht nie wegen eines Tool-Fehlers.

    Faengt ALLE Exceptions ab und gibt sie als JSON zurueck,
    damit Claude den Fehler dem User erklaeren kann.
    """
    try:
        ergebnis = tool_ausfuehren(name, eingabe)
        return ergebnis
    except Exception as exc:
        logger.error("Tool '%s' Exception: %s", name, exc, exc_info=True)
        return json.dumps(
            {
                "fehler": True,
                "tool": name,
                "nachricht": f"Tool-Ausfuehrung fehlgeschlagen: {exc}",
                "eingabe": str(eingabe)[:200],  # Defensive: Eingabe kuerzen
            },
            ensure_ascii=False,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Client erstellen (mit Validierung)
# ══════════════════════════════════════════════════════════════════════════════


def create_client() -> anthropic.Anthropic:
    """Erstellt einen Anthropic Client mit defensiver Validierung."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("FEHLER: .env Datei nicht gefunden.")
        print("Loesung: cp .env.example .env und API Key eintragen.")
        sys.exit(1)

    load_dotenv(env_path)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("FEHLER: ANTHROPIC_API_KEY ist leer.")
        print("Loesung: API Key in .env eintragen.")
        sys.exit(1)

    if api_key.startswith("sk-ant-api03-DEIN") or "EUER-KEY" in api_key:
        print("FEHLER: Placeholder-Key erkannt. Bitte echten API Key eintragen.")
        sys.exit(1)

    return anthropic.Anthropic(api_key=api_key)


# ══════════════════════════════════════════════════════════════════════════════
# SILVER: Conversation History (global, bleibt zwischen Fragen erhalten)
# ══════════════════════════════════════════════════════════════════════════════

conversation_history: list[dict[str, Any]] = []


# ══════════════════════════════════════════════════════════════════════════════
# DER AGENT LOOP — Herzstueck des Agents
# ══════════════════════════════════════════════════════════════════════════════
#
# Diagramm:
#   1. User stellt Frage
#   2. Claude bekommt Frage + Tool-Definitionen
#   3. Claude antwortet:
#      - stop_reason == "end_turn"  -> Finale Antwort, Loop Ende
#      - stop_reason == "tool_use" -> Claude will ein Tool benutzen
#   4. Wir fuehren das Tool LOKAL aus
#   5. Wir schicken das Ergebnis zurueck (tool_result)
#   6. Zurueck zu Schritt 3


def agent_fragen(
    user_frage: str,
    client: anthropic.Anthropic,
) -> str | None:
    """Sendet eine Frage an den Agent und verarbeitet den Tool-Use Loop.

    SILVER: Nutzt globale conversation_history fuer Gedaechtnis.
    GOLD: Nutzt tool_ausfuehren_sicher fuer crashsicheren Betrieb.

    Args:
        user_frage: Die Frage des Users.
        client: Der Anthropic API Client.

    Returns:
        Die finale Antwort als String, oder None bei Fehler.
    """
    print(f"\n{'=' * 60}")
    print(f"USER: {user_frage}")
    print(f"{'=' * 60}")

    # SILVER: Nachricht zur GLOBALEN History hinzufuegen
    conversation_history.append({"role": "user", "content": user_frage})

    durchlauf = 0
    gesamte_tokens = 0

    while durchlauf < MAX_LOOP_ITERATIONS:
        durchlauf += 1
        print(f"\n--- Loop Durchlauf {durchlauf}/{MAX_LOOP_ITERATIONS} ---")

        # API-Aufruf MIT Tool-Definitionen und Error Handling
        try:
            antwort = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=conversation_history,
            )
        except anthropic.AuthenticationError:
            print("FEHLER: API Key ungueltig (401 Unauthorized).")
            print("Loesung: Pruefe den Key unter https://console.anthropic.com/settings/keys")
            return None
        except anthropic.RateLimitError:
            print("FEHLER: Rate Limit erreicht (429). Bitte kurz warten.")
            return None
        except anthropic.APIConnectionError as exc:
            print(f"FEHLER: Keine Verbindung zur API: {exc}")
            return None
        except anthropic.APIStatusError as exc:
            print(f"FEHLER: API-Fehler (Status {exc.status_code}): {exc.message}")
            return None

        # Token-Tracking
        tokens_dieser_call = antwort.usage.input_tokens + antwort.usage.output_tokens
        gesamte_tokens += tokens_dieser_call
        print(f"Stop Reason: {antwort.stop_reason} | Tokens: {tokens_dieser_call}")

        # ── FALL 1: Claude ist fertig — finale Antwort ──
        if antwort.stop_reason == "end_turn":
            # SILVER: Finale Antwort zur History hinzufuegen
            conversation_history.append(
                {"role": "assistant", "content": antwort.content}
            )
            final_text = ""
            for block in antwort.content:
                if hasattr(block, "text"):
                    final_text += block.text

            print(f"\nAGENT: {final_text}")
            print(
                f"\n[Gesamt: {durchlauf} Durchlauf/Durchlaeufe, "
                f"{gesamte_tokens} Tokens]"
            )
            return final_text

        # ── FALL 2: Claude will Tools benutzen ──
        elif antwort.stop_reason == "tool_use":
            # Assistenten-Antwort zur History hinzufuegen
            conversation_history.append(
                {"role": "assistant", "content": antwort.content}
            )

            # Alle Tool-Aufrufe verarbeiten (inkl. Parallel Tool Use)
            tool_ergebnisse: list[dict[str, Any]] = []
            for block in antwort.content:
                if block.type == "tool_use":
                    print(f"  -> Tool: {block.name}")
                    print(
                        f"     Input: "
                        f"{json.dumps(block.input, ensure_ascii=False)}"
                    )

                    # GOLD: Sichere Tool-Ausfuehrung (crasht nie)
                    ergebnis = tool_ausfuehren_sicher(block.name, block.input)
                    print(
                        f"     Ergebnis: "
                        f"{ergebnis[:200]}{'...' if len(ergebnis) > 200 else ''}"
                    )

                    # WICHTIG: tool_use_id MUSS mit block.id uebereinstimmen
                    tool_ergebnisse.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": ergebnis,
                        }
                    )

            # Tool-Ergebnisse zurueck an Claude schicken
            conversation_history.append(
                {"role": "user", "content": tool_ergebnisse}
            )

        # ── FALL 3: Unerwarteter stop_reason (Defensive) ──
        else:
            logger.warning("Unerwarteter stop_reason: %s", antwort.stop_reason)
            return f"Unerwarteter stop_reason: {antwort.stop_reason}"

    # Sicherheitsschleife — verhindert Endlosloops
    print("WARNUNG: Maximale Durchlaeufe erreicht. Agent gestoppt.")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# GOLD: Structured Output mit tool_choice
# ══════════════════════════════════════════════════════════════════════════════


def strukturierte_analyse(
    text: str,
    client: anthropic.Anthropic,
) -> dict[str, Any] | None:
    """Erzwingt strukturiertes JSON Output ueber tool_choice.

    Claude MUSS das analyse_ergebnis Tool verwenden, dadurch ist
    das Ergebnis GARANTIERT valides JSON im definierten Schema.

    Args:
        text: Der zu analysierende Text.
        client: Der Anthropic API Client.

    Returns:
        Dict mit zusammenfassung, stichpunkte, bewertung. Oder None bei Fehler.
    """
    try:
        antwort = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=[ANALYSE_OUTPUT_TOOL],
            tool_choice={"type": "tool", "name": "analyse_ergebnis"},  # ERZWINGEN
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Analysiere diesen Text und gib eine "
                        "strukturierte Bewertung:\n\n" + text
                    ),
                }
            ],
        )
    except anthropic.APIError as exc:
        logger.error("API-Fehler bei strukturierter Analyse: %s", exc)
        return None

    # Ergebnis extrahieren — ist GARANTIERT valides JSON
    for block in antwort.content:
        if block.type == "tool_use":
            return block.input  # type: ignore[return-value]

    logger.warning("Kein tool_use Block in der Antwort gefunden.")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Interaktiver Modus
# ══════════════════════════════════════════════════════════════════════════════


def main() -> None:
    """Interaktiver Agent im Terminal."""
    tool_namen = [t["name"] for t in TOOLS]
    print("=" * 60)
    print("  AGENT GESTARTET")
    print(f"  {len(TOOLS)} Tools: {', '.join(tool_namen)}")
    print("  Features: Conversation History, Error Handling")
    print("  Tippt 'quit' zum Beenden")
    print("  Tippt 'analyse: <text>' fuer Structured Output (Gold)")
    print("  Tippt 'history' um Conversation History zu sehen")
    print("  Tippt 'clear' um History zu loeschen")
    print("=" * 60)

    client = create_client()

    while True:
        try:
            frage = input("\nDeine Frage: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAgent beendet.")
            break

        if not frage:
            continue

        if frage.lower() in ("quit", "exit", "q"):
            print("Agent beendet.")
            break

        # GOLD: Structured Output Modus
        if frage.lower().startswith("analyse:"):
            text = frage[len("analyse:"):].strip()
            if not text:
                print("Bitte Text nach 'analyse:' eingeben.")
                continue
            print("\n--- Structured Output (tool_choice) ---")
            ergebnis = strukturierte_analyse(text, client)
            if ergebnis:
                print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
            else:
                print("Analyse fehlgeschlagen.")
            continue

        # SILVER: Conversation History anzeigen
        if frage.lower() == "history":
            print(f"\nConversation History: {len(conversation_history)} Eintraege")
            for i, msg in enumerate(conversation_history):
                role = msg["role"]
                content = msg["content"]
                if isinstance(content, str):
                    preview = content[:80]
                elif isinstance(content, list):
                    preview = f"[{len(content)} Bloecke]"
                else:
                    preview = str(content)[:80]
                print(f"  {i + 1}. [{role}] {preview}")
            continue

        # SILVER: History loeschen
        if frage.lower() == "clear":
            conversation_history.clear()
            print("Conversation History geloescht.")
            continue

        # Standard: Agent Loop
        agent_fragen(frage, client)


if __name__ == "__main__":
    main()
