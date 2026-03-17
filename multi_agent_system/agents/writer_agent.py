"""
agents/writer_agent.py — Writer Agent (Markdown-Formatierung + Report-Erstellung).

Hat EIGENE Tools und EIGENE messages Liste (Context Isolation).

Defensive Coding:
    - Granulares API Error Handling
    - Sichere Tool-Ausfuehrung
    - Max Iterations als Sicherheitsbremse
    - Context Window Management (Sliding Window)

Datum: 17.03.2026 | Sebastian
"""

import json
import logging

import anthropic

# Windows-safe print (verhindert UnicodeEncodeError bei Emojis)
from multi_agent_system.utils.safe_print import safe_print as print  # noqa: A001

from multi_agent_system.config import (
    client,
    MODEL,
    MAX_TOKENS,
    MAX_ITERATIONS,
    WRITER_PROMPT,
)
from multi_agent_system.tools.writer_tools import writer_tools, run_writer_tool
from multi_agent_system.utils.context_manager import manage_context
from multi_agent_system.utils.token_tracker import track_tokens

logger = logging.getLogger(__name__)


def writer_agent_run(
    task: str,
    research_results: str = "",
    analysis_results: str = "",
    history: list | None = None,
) -> str:
    """Erstellt einen Report basierend auf Research- und Analyse-Ergebnissen.

    Args:
        task: Die Schreibaufgabe als String.
        research_results: Ergebnisse vom Research Agent.
        analysis_results: Ergebnisse vom Analysis Agent.
        history: Optionale persistente History (Silver).

    Returns:
        Der fertige Report als String.
    """
    # Task + Context kombinieren
    parts = [task]
    if research_results:
        parts.append(f"\n\nRecherche-Ergebnisse:\n{research_results}")
    if analysis_results:
        parts.append(f"\n\nAnalyse-Ergebnisse:\n{analysis_results}")
    full_task = "".join(parts)

    print(f"\n  [Writer Agent] Task: {full_task[:150]}...")

    # EIGENE messages Liste — Context Isolation!
    if history is not None:
        messages = history
        messages.append({"role": "user", "content": full_task})
    else:
        messages = [{"role": "user", "content": full_task}]

    for iteration in range(MAX_ITERATIONS):
        print(f"  [Writer Agent] Iteration {iteration + 1}/{MAX_ITERATIONS}")

        # Gold: Context Window Management
        messages = manage_context(messages)

        # API Call mit granularem Error Handling
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=WRITER_PROMPT,
                tools=writer_tools,
                messages=messages,
            )
        except anthropic.AuthenticationError:
            logger.error("Writer Agent: API Key ungueltig (401)")
            return "Error: API Key ungueltig."
        except anthropic.RateLimitError:
            logger.error("Writer Agent: Rate Limit (429)")
            return "Error: Rate Limit erreicht. Bitte kurz warten."
        except anthropic.APIConnectionError as exc:
            logger.error("Writer Agent: Verbindungsfehler: %s", exc)
            return f"Error: Keine Verbindung zur API: {exc}"
        except anthropic.APIStatusError as exc:
            logger.error("Writer Agent: API-Fehler %s", exc.status_code)
            return f"Error: API-Fehler (Status {exc.status_code})"

        # Gold: Token Tracking
        track_tokens("writer", response)
        tokens = response.usage.input_tokens + response.usage.output_tokens
        print(f"  [Writer Agent] Stop: {response.stop_reason} | Tokens: {tokens}")

        # ── FALL 1: Fertig ──
        if response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})

            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            print(f"  [Writer Agent] Done: {final_text[:150]}...")
            return final_text

        # ── FALL 2: Tool Use ──
        elif response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"    Tool: {block.name}")

                    result = run_writer_tool(block.name, block.input)
                    print(f"    Result: {result[:150]}...")

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            messages.append({"role": "user", "content": tool_results})

        # ── FALL 3: Unerwarteter stop_reason ──
        else:
            logger.warning("Writer Agent: Unerwarteter stop_reason: %s", response.stop_reason)
            return f"Error: Unerwarteter stop_reason: {response.stop_reason}"

    logger.warning("Writer Agent: Max iterations reached.")
    return "Writer Agent: Max iterations reached."
