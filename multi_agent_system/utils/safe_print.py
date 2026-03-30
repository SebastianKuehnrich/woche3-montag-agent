"""
utils/safe_print.py — Windows-kompatible Print-Funktion.

Verhindert UnicodeEncodeError auf Windows (cp1252 kann keine Emojis).
Ersetzt nicht-encodierbare Zeichen durch '?'.

Datum: 17.03.2026 | Sebastian
"""

import sys


def safe_print(*args, **kwargs) -> None:
    """Print-Wrapper der auf Windows Unicode-Fehler abfaengt.

    Ersetzt Zeichen die nicht im aktuellen Encoding darstellbar sind
    durch '?' statt zu crashen.
    """
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback: Encode mit errors='replace'
        text = " ".join(str(a) for a in args)
        encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding)
        print(safe_text, **kwargs)
