"""
tools/research_tools.py — Tools fuer den Research Agent.

Tools:
    - web_search: DuckDuckGo Internet-Suche
    - summarize: Text in Key Points zusammenfassen

Defensive Coding:
    - Input-Validierung (leerer String, Laenge)
    - max_results auf 1-5 begrenzt
    - Exception-Handling fuer Netzwerkfehler
    - Import-Fehler abgefangen

Datum: 17.03.2026 | Sebastian
"""

import json
import logging

logger = logging.getLogger(__name__)

# ═══ TOOL SCHEMAS ════════════════════════════════════════════════════════════

research_tools = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current information using DuckDuckGo. "
            "Returns titles, URLs, and text snippets. "
            "Use for any fact-finding, news, or information gathering task."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (1-5). Default: 3",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "summarize",
        "description": (
            "Summarize a given text into key bullet points. "
            "Use after web_search to condense results into actionable insights."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to summarize",
                },
                "max_points": {
                    "type": "integer",
                    "description": "Maximum number of bullet points. Default: 5",
                },
            },
            "required": ["text"],
        },
    },
]


# ═══ TOOL IMPLEMENTATIONS ════════════════════════════════════════════════════


def _tool_web_search(tool_input: dict) -> str:
    """Sucht im Internet via DuckDuckGo.

    Defensive: Input-Validierung, max_results begrenzt, Netzwerkfehler abgefangen.
    """
    query = tool_input.get("query", "")
    max_results = tool_input.get("max_results", 3)

    # Defensive: Input-Validierung
    if not isinstance(query, str) or not query.strip():
        return json.dumps({"error": "Empty search query."}, ensure_ascii=False)

    if len(query) > 200:
        return json.dumps(
            {"error": "Query too long (max 200 chars)."},
            ensure_ascii=False,
        )

    # Defensive: max_results begrenzen
    if not isinstance(max_results, int) or max_results < 1:
        max_results = 3
    max_results = min(max_results, 5)

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))

        if not raw_results:
            return json.dumps(
                {"query": query, "results": [], "hint": "No results found."},
                ensure_ascii=False,
            )

        clean_results = []
        for r in raw_results:
            clean_results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
            )

        return json.dumps(
            {
                "query": query,
                "result_count": len(clean_results),
                "results": clean_results,
            },
            ensure_ascii=False,
        )

    except ImportError:
        return json.dumps(
            {"error": "duckduckgo_search not installed. pip install duckduckgo_search"},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.error("Web search failed: %s", exc)
        return json.dumps(
            {"error": f"Web search failed: {exc}"},
            ensure_ascii=False,
        )


def _tool_summarize(tool_input: dict) -> str:
    """Fasst einen Text in Key Points zusammen.

    Defensive: Leerer Text, max_points begrenzt.
    """
    text = tool_input.get("text", "")
    max_points = tool_input.get("max_points", 5)

    # Defensive: Input-Validierung
    if not isinstance(text, str) or not text.strip():
        return json.dumps({"error": "Empty text to summarize."}, ensure_ascii=False)

    if len(text) > 50000:
        return json.dumps(
            {"error": "Text too long (max 50,000 chars)."},
            ensure_ascii=False,
        )

    # Defensive: max_points begrenzen
    if not isinstance(max_points, int) or max_points < 1:
        max_points = 5
    max_points = min(max_points, 10)

    # Einfache Satz-basierte Zusammenfassung
    sentences = text.replace("! ", ". ").replace("? ", ". ").split(". ")
    # Filtere leere und sehr kurze Saetze
    key_points = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    key_points = key_points[:max_points]

    return json.dumps(
        {
            "original_length": len(text),
            "summary_points": key_points,
            "point_count": len(key_points),
        },
        ensure_ascii=False,
    )


# ═══ TOOL REGISTRY ═══════════════════════════════════════════════════════════

_RESEARCH_TOOL_REGISTRY = {
    "web_search": _tool_web_search,
    "summarize": _tool_summarize,
}


def run_research_tool(name: str, tool_input: dict) -> str:
    """Fuehrt ein Research-Tool sicher aus.

    Args:
        name: Tool-Name (web_search, summarize)
        tool_input: Tool-Input als Dictionary

    Returns:
        JSON-String mit Ergebnis oder Fehler
    """
    if name not in _RESEARCH_TOOL_REGISTRY:
        return json.dumps(
            {"error": f"Unknown research tool: {name}"},
            ensure_ascii=False,
        )

    if not isinstance(tool_input, dict):
        return json.dumps(
            {"error": "Tool input must be a dictionary."},
            ensure_ascii=False,
        )

    try:
        return _RESEARCH_TOOL_REGISTRY[name](tool_input)
    except Exception as exc:
        logger.error("Research tool '%s' crashed: %s", name, exc, exc_info=True)
        return json.dumps(
            {"error": f"Tool '{name}' crashed: {exc}"},
            ensure_ascii=False,
        )
