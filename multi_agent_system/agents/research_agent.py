"""
agents/research_agent.py — Research Agent (Web-Recherche + Zusammenfassung).

Hat EIGENE Tools und EIGENE messages Liste (Context Isolation).
Der Research Agent sieht NICHTS vom Supervisor oder anderen Agents.

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
    RESEARCH_PROMPT,
)
from multi_agent_system.tools.research_tools import research_tools, run_research_tool
from multi_agent_system.utils.context_manager import manage_context
from multi_agent_system.utils.token_tracker import track_tokens

logger = logging.getLogger(__name__)


def research_agent_run(task: str, history: list | None = None) -> str:
    """Fuehrt eine Recherche-Aufgabe aus.

    Context Isolation: Eigene messages Liste, eigene Tools.
    Der Agent sieht NICHTS vom Supervisor.

    Args:
        task: Die Recherche-Aufgabe als String (vom Supervisor).
        history: Optionale persistente History (Silver).

    Returns:
        Das Recherche-Ergebnis als String.
    """
    print(f"\n  [Research Agent] Task: {task}")

    # EIGENE messages Liste — Context Isolation!
    # Silver: Nutze persistente History wenn vorhanden
    if history is not None:
        messages = history
        messages.append({"role": "user", "content": task})
    else:
        messages = [{"role": "user", "content": task}]

    for iteration in range(MAX_ITERATIONS):
        print(f"  [Research Agent] Iteration {iteration + 1}/{MAX_ITERATIONS}")

        # Gold: Context Window Management
        messages = manage_context(messages)

        # API Call mit granularem Error Handling
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=RESEARCH_PROMPT,
                tools=research_tools,
                messages=messages,
            )
        except anthropic.AuthenticationError:
            logger.error("Research Agent: API Key ungueltig (401)")
            return "Error: API Key ungueltig."
        except anthropic.RateLimitError:
            logger.error("Research Agent: Rate Limit (429)")
            return "Error: Rate Limit erreicht. Bitte kurz warten."
        except anthropic.APIConnectionError as exc:
            logger.error("Research Agent: Verbindungsfehler: %s", exc)
            return f"Error: Keine Verbindung zur API: {exc}"
        except anthropic.APIStatusError as exc:
            logger.error("Research Agent: API-Fehler %s", exc.status_code)
            return f"Error: API-Fehler (Status {exc.status_code})"

        # Gold: Token Tracking
        track_tokens("research", response)
        tokens = response.usage.input_tokens + response.usage.output_tokens
        print(f"  [Research Agent] Stop: {response.stop_reason} | Tokens: {tokens}")

        # ── FALL 1: Fertig — finale Antwort ──
        if response.stop_reason == "end_turn":
            # History aktualisieren
            messages.append({"role": "assistant", "content": response.content})

            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            print(f"  [Research Agent] Done: {final_text[:150]}...")
            return final_text

        # ── FALL 2: Tool Use ──
        elif response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"    Tool: {block.name}")
                    print(f"    Input: {json.dumps(block.input, ensure_ascii=False)[:150]}")

                    # Sichere Tool-Ausfuehrung
                    result = run_research_tool(block.name, block.input)
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
            logger.warning("Research Agent: Unerwarteter stop_reason: %s", response.stop_reason)
            return f"Error: Unerwarteter stop_reason: {response.stop_reason}"

    # Sicherheitsschleife
    logger.warning("Research Agent: Max iterations reached.")
    return "Research Agent: Max iterations reached — partial results may be available."
