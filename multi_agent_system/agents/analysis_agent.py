"""
agents/analysis_agent.py — Analysis Agent (Text-Analyse + Sentiment).

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
    ANALYSIS_PROMPT,
)
from multi_agent_system.tools.analysis_tools import analysis_tools, run_analysis_tool
from multi_agent_system.utils.context_manager import manage_context
from multi_agent_system.utils.token_tracker import track_tokens

logger = logging.getLogger(__name__)


def analysis_agent_run(task: str, context: str = "", history: list | None = None) -> str:
    """Fuehrt eine Analyse-Aufgabe aus.

    Args:
        task: Die Analyse-Aufgabe als String (vom Supervisor).
        context: Optionaler Context (z.B. Ergebnis vom Research Agent).
        history: Optionale persistente History (Silver).

    Returns:
        Das Analyse-Ergebnis als String.
    """
    # Task + Context kombinieren
    full_task = task
    if context:
        full_task = f"{task}\n\nContext/Text zum Analysieren:\n{context}"

    print(f"\n  [Analysis Agent] Task: {full_task[:150]}...")

    # EIGENE messages Liste — Context Isolation!
    if history is not None:
        messages = history
        messages.append({"role": "user", "content": full_task})
    else:
        messages = [{"role": "user", "content": full_task}]

    for iteration in range(MAX_ITERATIONS):
        print(f"  [Analysis Agent] Iteration {iteration + 1}/{MAX_ITERATIONS}")

        # Gold: Context Window Management
        messages = manage_context(messages)

        # API Call mit granularem Error Handling
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=ANALYSIS_PROMPT,
                tools=analysis_tools,
                messages=messages,
            )
        except anthropic.AuthenticationError:
            logger.error("Analysis Agent: API Key ungueltig (401)")
            return "Error: API Key ungueltig."
        except anthropic.RateLimitError:
            logger.error("Analysis Agent: Rate Limit (429)")
            return "Error: Rate Limit erreicht. Bitte kurz warten."
        except anthropic.APIConnectionError as exc:
            logger.error("Analysis Agent: Verbindungsfehler: %s", exc)
            return f"Error: Keine Verbindung zur API: {exc}"
        except anthropic.APIStatusError as exc:
            logger.error("Analysis Agent: API-Fehler %s", exc.status_code)
            return f"Error: API-Fehler (Status {exc.status_code})"

        # Gold: Token Tracking
        track_tokens("analysis", response)
        tokens = response.usage.input_tokens + response.usage.output_tokens
        print(f"  [Analysis Agent] Stop: {response.stop_reason} | Tokens: {tokens}")

        # ── FALL 1: Fertig ──
        if response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})

            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            print(f"  [Analysis Agent] Done: {final_text[:150]}...")
            return final_text

        # ── FALL 2: Tool Use ──
        elif response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"    Tool: {block.name}")

                    result = run_analysis_tool(block.name, block.input)
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
            logger.warning("Analysis Agent: Unerwarteter stop_reason: %s", response.stop_reason)
            return f"Error: Unerwarteter stop_reason: {response.stop_reason}"

    logger.warning("Analysis Agent: Max iterations reached.")
    return "Analysis Agent: Max iterations reached."
