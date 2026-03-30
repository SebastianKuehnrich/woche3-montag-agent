"""
config.py — Shared Configuration fuer das Multi-Agent Research System.

Alle Agents und der Supervisor verwenden diese Settings.
Defensive Coding: API Key Validierung, Fallback-Werte.

Datum: 17.03.2026 | Sebastian
"""

import os
import sys
from pathlib import Path

# ─── Dependency Checks ──────────────────────────────────────────────────────

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
    from duckduckgo_search import DDGS  # noqa: F401 — Import-Check
except ImportError:
    print("FEHLER: 'duckduckgo_search' nicht installiert. -> pip install duckduckgo_search")
    sys.exit(1)


# ─── .env laden ──────────────────────────────────────────────────────────────

env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent / ".env"

if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    print("WARNUNG: Keine .env Datei gefunden. ANTHROPIC_API_KEY muss als Umgebungsvariable gesetzt sein.")

# ─── API Key Validierung ─────────────────────────────────────────────────────

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("FEHLER: ANTHROPIC_API_KEY nicht gesetzt.")
    print("Loesung: .env Datei erstellen mit ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

if api_key.startswith("sk-ant-api03-DEIN") or "EUER-KEY" in api_key:
    print("FEHLER: Placeholder-Key erkannt. Bitte echten API Key eintragen.")
    sys.exit(1)

# ─── Client erstellen ────────────────────────────────────────────────────────

client = anthropic.Anthropic(api_key=api_key)

# ═══ SETTINGS ═══════════════════════════════════════════════════════════════

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024
MAX_ITERATIONS = 5  # Pro Sub-Agent
SUPERVISOR_MAX_ITERATIONS = 10  # Supervisor darf laenger laufen (Chaining)

# ═══ SYSTEM PROMPTS ══════════════════════════════════════════════════════════

SUPERVISOR_PROMPT = (
    "Du bist ein Supervisor-Agent. Deine EINZIGE Aufgabe ist es, Tasks an "
    "spezialisierte Agents zu routen. Du beantwortest KEINE Fragen selbst. "
    "Analysiere die User-Anfrage und entscheide welcher Agent sie bearbeiten soll. "
    "Du kannst mehrere Agents nacheinander aufrufen (Chaining): "
    "z.B. erst Research, dann Analysis, dann Writer. "
    "Uebergib immer die Ergebnisse vorheriger Agents als Context an den naechsten. "
    "Antworte immer auf Deutsch."
)

RESEARCH_PROMPT = (
    "Du bist ein Research-Spezialist. Nutze deine Tools um Informationen zu finden. "
    "Sei gruendlich aber praegnant. Gib strukturierte Ergebnisse zurueck. "
    "Antworte auf Deutsch."
)

ANALYSIS_PROMPT = (
    "Du bist ein Analyse-Spezialist. Nutze deine Tools um Texte zu analysieren. "
    "Liefere detaillierte, datengetriebene Analysen. "
    "Antworte auf Deutsch."
)

WRITER_PROMPT = (
    "Du bist ein Report-Writer. Nutze deine Tools um professionelle Markdown-Reports "
    "zu erstellen. Strukturiere Informationen klar und uebersichtlich. "
    "Antworte auf Deutsch."
)
