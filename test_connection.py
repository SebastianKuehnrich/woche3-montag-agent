"""
test_connection.py — Verbindungstest zur Anthropic API.

Defensive Coding:
- Prüft ob .env existiert und ANTHROPIC_API_KEY gesetzt ist
- Fängt alle relevanten Exceptions ab (Auth, Netzwerk, Rate Limit)
- Gibt klare Fehlermeldungen mit Lösungsvorschlägen
"""

import sys
import os
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("FEHLER: 'anthropic' Paket nicht installiert.")
    print("Lösung: pip install anthropic")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("FEHLER: 'python-dotenv' Paket nicht installiert.")
    print("Lösung: pip install python-dotenv")
    sys.exit(1)


def test_connection() -> bool:
    """Testet die Verbindung zur Anthropic API.

    Returns:
        True bei Erfolg, False bei Fehler.
    """
    # 1. Prüfe ob .env existiert
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("FEHLER: .env Datei nicht gefunden.")
        print("Lösung: cp .env.example .env und API Key eintragen.")
        return False

    load_dotenv(env_path)

    # 2. Prüfe ob API Key gesetzt ist
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("FEHLER: ANTHROPIC_API_KEY ist leer.")
        print("Lösung: API Key in .env eintragen.")
        return False

    if api_key.startswith("sk-ant-api03-DEIN") or api_key == "sk-ant-api03-EUER-KEY-HIER":
        print("FEHLER: Placeholder-Key erkannt. Bitte echten API Key eintragen.")
        return False

    # 3. API-Aufruf mit Error Handling
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Sag 'Verbindung steht!' auf Deutsch."}
            ],
        )
    except anthropic.AuthenticationError:
        print("FEHLER: API Key ungültig (401 Unauthorized).")
        print("Lösung: Prüfe den Key unter https://console.anthropic.com/settings/keys")
        return False
    except anthropic.RateLimitError:
        print("FEHLER: Rate Limit erreicht (429).")
        print("Lösung: Warte kurz und versuche es erneut.")
        return False
    except anthropic.APIConnectionError as e:
        print(f"FEHLER: Keine Verbindung zur API: {e}")
        print("Lösung: Prüfe deine Internetverbindung.")
        return False
    except anthropic.APIStatusError as e:
        print(f"FEHLER: API-Fehler (Status {e.status_code}): {e.message}")
        return False

    # 4. Ergebnis ausgeben
    text = response.content[0].text
    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    print(f"Antwort: {text}")
    print(f"Tokens verwendet: {tokens_used}")
    print("Verbindungstest erfolgreich!")
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
