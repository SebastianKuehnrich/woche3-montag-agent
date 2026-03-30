"""
tools/writer_tools.py — Tools fuer den Writer Agent.

Tools:
    - format_markdown: Text in formatierten Markdown umwandeln
    - create_report: Strukturierten Report aus Sections erstellen

Defensive Coding:
    - Input-Validierung
    - Sections-Array Pruefung
    - Maximale Report-Groesse

Datum: 17.03.2026 | Sebastian
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ═══ TOOL SCHEMAS ════════════════════════════════════════════════════════════

writer_tools = [
    {
        "name": "format_markdown",
        "description": (
            "Format text as clean Markdown with headlines, bullet points, "
            "and bold text. Use to clean up raw text into readable format."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The raw text to format",
                },
                "style": {
                    "type": "string",
                    "enum": ["bullet_points", "paragraphs", "numbered"],
                    "description": "Output style. Default: bullet_points",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "create_report",
        "description": (
            "Create a structured report from sections. "
            "Each section has a title and content. "
            "Returns a complete markdown report with header, table of contents, "
            "and formatted sections."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Report title",
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["heading", "content"],
                    },
                    "description": "Report sections with heading and content",
                },
                "author": {
                    "type": "string",
                    "description": "Author name. Default: Multi-Agent System",
                },
            },
            "required": ["title", "sections"],
        },
    },
]


# ═══ TOOL IMPLEMENTATIONS ════════════════════════════════════════════════════


def _tool_format_markdown(tool_input: dict) -> str:
    """Formatiert rohen Text als sauberes Markdown."""
    text = tool_input.get("text", "")
    style = tool_input.get("style", "bullet_points")

    # Defensive: Input-Validierung
    if not isinstance(text, str) or not text.strip():
        return json.dumps({"error": "Empty text."}, ensure_ascii=False)

    if len(text) > 50000:
        return json.dumps(
            {"error": "Text too long (max 50,000 chars)."},
            ensure_ascii=False,
        )

    # Text in Saetze aufteilen
    sentences = [s.strip() for s in text.replace("! ", ". ").replace("? ", ". ").split(". ") if s.strip()]

    if style == "numbered":
        formatted_lines = [f"{i + 1}. {s}" for i, s in enumerate(sentences)]
    elif style == "paragraphs":
        formatted_lines = [f"{s}.\n" for s in sentences]
    else:  # bullet_points (default)
        formatted_lines = [f"- {s}" for s in sentences]

    formatted = "\n".join(formatted_lines)

    return json.dumps(
        {
            "formatted_text": formatted,
            "style": style,
            "line_count": len(formatted_lines),
        },
        ensure_ascii=False,
    )


def _tool_create_report(tool_input: dict) -> str:
    """Erstellt einen strukturierten Markdown-Report aus Sections."""
    title = tool_input.get("title", "Report")
    sections = tool_input.get("sections", [])
    author = tool_input.get("author", "Multi-Agent Research System")

    # Defensive: Input-Validierung
    if not isinstance(title, str) or not title.strip():
        return json.dumps({"error": "Empty report title."}, ensure_ascii=False)

    if not isinstance(sections, list) or len(sections) == 0:
        return json.dumps(
            {"error": "Sections must be a non-empty array."},
            ensure_ascii=False,
        )

    if len(sections) > 20:
        return json.dumps(
            {"error": "Too many sections (max 20)."},
            ensure_ascii=False,
        )

    # Report-Header
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    report_parts = [
        f"# {title.strip()}",
        "",
        f"**Autor:** {author}  ",
        f"**Datum:** {now}  ",
        f"**Generiert von:** Multi-Agent Research System",
        "",
        "---",
        "",
        "## Inhaltsverzeichnis",
        "",
    ]

    # Table of Contents
    for i, section in enumerate(sections, 1):
        heading = section.get("heading", f"Abschnitt {i}")
        # Einfachen Anker aus Heading erstellen
        anchor = heading.lower().replace(" ", "-").replace(".", "").replace(",", "")
        report_parts.append(f"{i}. [{heading}](#{anchor})")

    report_parts.append("")
    report_parts.append("---")
    report_parts.append("")

    # Sections
    for i, section in enumerate(sections, 1):
        heading = section.get("heading", f"Abschnitt {i}")
        content = section.get("content", "")

        # Defensive: Content validieren
        if not isinstance(content, str):
            content = str(content)

        report_parts.append(f"## {heading}")
        report_parts.append("")
        report_parts.append(content)
        report_parts.append("")

    # Footer
    report_parts.append("---")
    report_parts.append(f"*Report erstellt am {now} von {author}*")

    full_report = "\n".join(report_parts)

    return json.dumps(
        {
            "report": full_report,
            "title": title,
            "section_count": len(sections),
            "character_count": len(full_report),
        },
        ensure_ascii=False,
    )


# ═══ TOOL REGISTRY ═══════════════════════════════════════════════════════════

_WRITER_TOOL_REGISTRY = {
    "format_markdown": _tool_format_markdown,
    "create_report": _tool_create_report,
}


def run_writer_tool(name: str, tool_input: dict) -> str:
    """Fuehrt ein Writer-Tool sicher aus."""
    if name not in _WRITER_TOOL_REGISTRY:
        return json.dumps(
            {"error": f"Unknown writer tool: {name}"},
            ensure_ascii=False,
        )

    if not isinstance(tool_input, dict):
        return json.dumps(
            {"error": "Tool input must be a dictionary."},
            ensure_ascii=False,
        )

    try:
        return _WRITER_TOOL_REGISTRY[name](tool_input)
    except Exception as exc:
        logger.error("Writer tool '%s' crashed: %s", name, exc, exc_info=True)
        return json.dumps(
            {"error": f"Tool '{name}' crashed: {exc}"},
            ensure_ascii=False,
        )
