"""
utils/context_manager.py — Sliding Window Context Management (Gold).

Verhindert Context Window Overflow durch:
    - Token-Schaetzung pro Message
    - Sliding Window: Erste Nachricht + letzte N behalten
    - Schutz gegen unbegrenztes History-Wachstum

Datum: 17.03.2026 | Sebastian
"""

import json
import logging

logger = logging.getLogger(__name__)

# Maximale geschaetzte Tokens bevor Sliding Window greift
DEFAULT_MAX_TOKENS = 50000


def manage_context(
    messages: list,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    keep_recent: int = 4,
) -> list:
    """Sliding Window: Behaelt erste + letzte N Nachrichten.

    Was hier passiert:
        - Schaetzt die Token-Anzahl der messages (1 Token ~ 4 Zeichen)
        - Wenn zu viele: Entfernt die aeltesten Nachrichten
        - Behaelt IMMER die erste User-Nachricht (Original-Task)
        - Behaelt IMMER die letzten N Nachrichten (aktueller Kontext)

    Args:
        messages: Die aktuelle messages Liste.
        max_tokens: Maximale Token-Anzahl (geschaetzt). Default: 50000.
        keep_recent: Anzahl der letzten Nachrichten die behalten werden. Default: 4.

    Returns:
        Gekuerzte messages Liste (oder original wenn noch Platz).
    """
    if not messages:
        return messages

    # Grobe Schaetzung: 1 Token ~ 4 Zeichen
    estimated_tokens = sum(_estimate_message_tokens(m) for m in messages)

    if estimated_tokens <= max_tokens:
        return messages  # Passt noch

    # Sliding Window noetig
    original_count = len(messages)
    logger.info(
        "Context Window Management: ~%d Tokens (Limit: %d), %d Messages -> Sliding Window",
        estimated_tokens,
        max_tokens,
        original_count,
    )

    # Erste Nachricht (Original-Task) + letzte N behalten
    if len(messages) <= keep_recent + 1:
        return messages  # Nicht genug zum Kuerzen

    first_message = messages[0]
    recent = messages[-keep_recent:]

    trimmed = [first_message] + recent

    new_tokens = sum(_estimate_message_tokens(m) for m in trimmed)
    logger.info(
        "Context Window: %d -> %d Messages, ~%d -> ~%d Tokens",
        original_count,
        len(trimmed),
        estimated_tokens,
        new_tokens,
    )

    return trimmed


def _estimate_message_tokens(message: dict) -> int:
    """Schaetzt die Token-Anzahl einer Nachricht.

    Grobe Heuristik: 1 Token ~ 4 Zeichen.
    Nicht exakt, aber gut genug fuer Sliding Window.
    """
    try:
        content = message.get("content", "")
        if isinstance(content, str):
            return len(content) // 4
        elif isinstance(content, list):
            # Liste von Content Blocks oder Tool Results
            return len(json.dumps(content, ensure_ascii=False)) // 4
        else:
            return len(str(content)) // 4
    except Exception:
        return 100  # Defensive Fallback
