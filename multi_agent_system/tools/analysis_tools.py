"""
tools/analysis_tools.py — Tools fuer den Analysis Agent.

Tools:
    - text_analysis: Wortanzahl, Satzanzahl, Top-5 Woerter, Statistiken
    - sentiment_analysis: Einfache Sentiment-Erkennung (positive/negative Woerter)

Defensive Coding:
    - Input-Validierung (leerer Text, Laenge)
    - Sichere Wort-Zaehlung ohne externe Dependencies
    - Exception-Handling

Datum: 17.03.2026 | Sebastian
"""

import json
import logging

logger = logging.getLogger(__name__)

# ═══ TOOL SCHEMAS ════════════════════════════════════════════════════════════

analysis_tools = [
    {
        "name": "text_analysis",
        "description": (
            "Analyze text and return detailed statistics: word count, "
            "character count, sentence count, average word length, "
            "and top 5 most frequent words. Use for any text analysis task."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to analyze",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "sentiment_analysis",
        "description": (
            "Analyze the sentiment of a text. Counts positive and negative "
            "words to determine overall sentiment (positive/negative/neutral). "
            "Use when the user wants to know the tone or mood of a text."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to analyze for sentiment",
                },
            },
            "required": ["text"],
        },
    },
]


# ═══ TOOL IMPLEMENTATIONS ════════════════════════════════════════════════════


def _tool_text_analysis(tool_input: dict) -> str:
    """Analysiert einen Text und gibt detaillierte Statistiken zurueck.

    Basiert auf dem text_analyse Tool aus agent.py (Tag 1).
    """
    text = tool_input.get("text", "")

    # Defensive: Input-Validierung
    if not isinstance(text, str) or not text.strip():
        return json.dumps({"error": "Empty text."}, ensure_ascii=False)

    if len(text) > 50000:
        return json.dumps(
            {"error": "Text too long (max 50,000 chars)."},
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
        clean = wort.lower().strip(".,!?;:()[]\"'-")
        if len(clean) > 2:
            zaehlung[clean] = zaehlung.get(clean, 0) + 1
    top_5 = sorted(zaehlung.items(), key=lambda x: x[1], reverse=True)[:5]

    return json.dumps(
        {
            "word_count": len(woerter),
            "character_count": zeichen,
            "sentence_count": max(saetze, 1),
            "average_word_length": round(avg_wortlaenge, 1),
            "top_5_words": [{"word": w, "count": c} for w, c in top_5],
            "words_per_sentence": round(len(woerter) / max(saetze, 1), 1),
        },
        ensure_ascii=False,
    )


# Einfache Wortlisten fuer Sentiment (kein ML noetig fuer Bronze)
_POSITIVE_WORDS = {
    "gut", "super", "toll", "excellent", "great", "amazing", "wonderful",
    "fantastic", "positiv", "erfolg", "erfolgreich", "vorteil", "chance",
    "innovation", "fortschritt", "wachstum", "verbesserung", "stark",
    "effizient", "optimistisch", "revolutionaer", "durchbruch", "gewinn",
    "good", "best", "better", "improve", "benefit", "advantage", "progress",
    "growth", "success", "powerful", "promising", "innovative", "effective",
    "efficient", "advanced", "remarkable", "significant", "impressive",
}

_NEGATIVE_WORDS = {
    "schlecht", "problem", "fehler", "risiko", "gefahr", "verlust",
    "nachteil", "schwaeche", "krise", "bedrohung", "negativ", "scheitern",
    "versagen", "mangel", "kritik", "sorge", "angst", "warnung",
    "bad", "worst", "worse", "fail", "failure", "risk", "danger", "threat",
    "crisis", "loss", "concern", "worry", "challenge", "difficult",
    "problem", "issue", "limitation", "drawback", "weakness", "decline",
}


def _tool_sentiment_analysis(tool_input: dict) -> str:
    """Einfache Sentiment-Analyse basierend auf Wortlisten.

    Zaehlt positive und negative Woerter, berechnet Score.
    """
    text = tool_input.get("text", "")

    # Defensive: Input-Validierung
    if not isinstance(text, str) or not text.strip():
        return json.dumps({"error": "Empty text."}, ensure_ascii=False)

    if len(text) > 50000:
        return json.dumps(
            {"error": "Text too long (max 50,000 chars)."},
            ensure_ascii=False,
        )

    woerter = text.lower().split()
    positive_count = 0
    negative_count = 0
    positive_found: list[str] = []
    negative_found: list[str] = []

    for wort in woerter:
        clean = wort.strip(".,!?;:()[]\"'-")
        if clean in _POSITIVE_WORDS:
            positive_count += 1
            if clean not in positive_found:
                positive_found.append(clean)
        elif clean in _NEGATIVE_WORDS:
            negative_count += 1
            if clean not in negative_found:
                negative_found.append(clean)

    total = positive_count + negative_count
    if total == 0:
        sentiment = "neutral"
        score = 0.0
    else:
        score = (positive_count - negative_count) / total
        if score > 0.2:
            sentiment = "positive"
        elif score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

    return json.dumps(
        {
            "sentiment": sentiment,
            "score": round(score, 2),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "positive_words": positive_found[:10],
            "negative_words": negative_found[:10],
            "total_words_analyzed": len(woerter),
        },
        ensure_ascii=False,
    )


# ═══ TOOL REGISTRY ═══════════════════════════════════════════════════════════

_ANALYSIS_TOOL_REGISTRY = {
    "text_analysis": _tool_text_analysis,
    "sentiment_analysis": _tool_sentiment_analysis,
}


def run_analysis_tool(name: str, tool_input: dict) -> str:
    """Fuehrt ein Analysis-Tool sicher aus."""
    if name not in _ANALYSIS_TOOL_REGISTRY:
        return json.dumps(
            {"error": f"Unknown analysis tool: {name}"},
            ensure_ascii=False,
        )

    if not isinstance(tool_input, dict):
        return json.dumps(
            {"error": "Tool input must be a dictionary."},
            ensure_ascii=False,
        )

    try:
        return _ANALYSIS_TOOL_REGISTRY[name](tool_input)
    except Exception as exc:
        logger.error("Analysis tool '%s' crashed: %s", name, exc, exc_info=True)
        return json.dumps(
            {"error": f"Tool '{name}' crashed: {exc}"},
            ensure_ascii=False,
        )
