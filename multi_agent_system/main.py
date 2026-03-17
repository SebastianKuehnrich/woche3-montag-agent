"""
Multi-Agent Research System — Supervisor (main.py)

Der Supervisor routet User-Anfragen an spezialisierte Agents:
    - Research Agent: Web-Suche, Zusammenfassung
    - Analysis Agent: Text-Analyse, Sentiment
    - Writer Agent: Markdown-Formatierung, Report-Erstellung

Architektur: Supervisor-Worker Pattern mit Context Isolation.
Jeder Agent hat eigene Tools, eigene messages, eigenen Loop.

Tiers:
    BRONZE: Supervisor + 2 Agents (Research, Analysis)
    SILVER: 3. Agent (Writer) + Chaining + persistente History
    GOLD:   Error Handling + Retry + Token Tracking + Context Management

Datum: 17.03.2026 | Sebastian
"""

import json
import logging
import sys

import anthropic

# Windows-safe print (verhindert UnicodeEncodeError bei Emojis)
from multi_agent_system.utils.safe_print import safe_print as print  # noqa: A001

from multi_agent_system.config import (
    client,
    MODEL,
    MAX_TOKENS,
    SUPERVISOR_MAX_ITERATIONS,
    SUPERVISOR_PROMPT,
)
from multi_agent_system.agents.research_agent import research_agent_run
from multi_agent_system.agents.analysis_agent import analysis_agent_run
from multi_agent_system.agents.writer_agent import writer_agent_run
from multi_agent_system.utils.token_tracker import (
    track_tokens,
    print_token_summary,
    reset_token_usage,
)
from multi_agent_system.utils.context_manager import manage_context

# ─── Logging Setup ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ═══ SUPERVISOR ROUTING TOOLS ═══════════════════════════════════════════════
# Das sind KEINE echten Tools — jedes "Tool" ruft einen Sub-Agent auf.

supervisor_tools = [
    {
        "name": "call_research_agent",
        "description": (
            "Route a task to the Research Agent. Use when the user needs "
            "web search, information gathering, fact-finding, or news. "
            "The Research Agent has tools: web_search, summarize."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Clear description of the research task",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_analysis_agent",
        "description": (
            "Route a task to the Analysis Agent. Use when text needs to be "
            "analyzed: word counts, sentiment, key facts, statistics. "
            "The Analysis Agent has tools: text_analysis, sentiment_analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Clear description of the analysis task",
                },
                "context": {
                    "type": "string",
                    "description": "Text or data that the agent should analyze",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_writer_agent",
        "description": (
            "Route a writing task to the Writer Agent. Use when research "
            "and analysis are complete and a report needs to be created. "
            "The Writer Agent has tools: format_markdown, create_report."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The writing task",
                },
                "research_results": {
                    "type": "string",
                    "description": "Results from the Research Agent",
                },
                "analysis_results": {
                    "type": "string",
                    "description": "Results from the Analysis Agent",
                },
            },
            "required": ["task"],
        },
    },
]


# ═══ SILVER: Persistente Agent Histories ═════════════════════════════════════

agent_histories: dict[str, list] = {
    "supervisor": [],
    "research": [],
    "analysis": [],
    "writer": [],
}


# ═══ GOLD: Agent Ausfuehrung mit Retry + Fallback ═══════════════════════════

MAX_RETRIES = 2


def execute_agent(agent_name: str, agent_input: dict) -> str:
    """Fuehrt einen Sub-Agent mit Retry-Logik aus.

    Gold: Bei Fehler bis zu MAX_RETRIES Versuche.
    Gibt bei komplettem Fehlschlag eine Fehler-Nachricht zurueck
    (kein Crash).

    Args:
        agent_name: Name des Routing-Tools (call_research_agent, etc.)
        agent_input: Tool-Input mit task, context, etc.

    Returns:
        Agent-Ergebnis als String.
    """
    task = agent_input.get("task", "")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if agent_name == "call_research_agent":
                return research_agent_run(
                    task=task,
                    history=agent_histories["research"],
                )

            elif agent_name == "call_analysis_agent":
                return analysis_agent_run(
                    task=task,
                    context=agent_input.get("context", ""),
                    history=agent_histories["analysis"],
                )

            elif agent_name == "call_writer_agent":
                return writer_agent_run(
                    task=task,
                    research_results=agent_input.get("research_results", ""),
                    analysis_results=agent_input.get("analysis_results", ""),
                    history=agent_histories["writer"],
                )

            else:
                return json.dumps(
                    {"error": f"Unknown agent: {agent_name}"},
                    ensure_ascii=False,
                )

        except Exception as exc:
            logger.error(
                "Agent '%s' failed (attempt %d/%d): %s",
                agent_name,
                attempt,
                MAX_RETRIES,
                exc,
            )
            if attempt == MAX_RETRIES:
                return json.dumps(
                    {
                        "error": f"Agent {agent_name} failed after {MAX_RETRIES} attempts: {exc}",
                        "fallback": "Supervisor should try alternative approach.",
                    },
                    ensure_ascii=False,
                )

    # Sollte nicht erreicht werden (Defensive)
    return json.dumps({"error": "Unexpected retry loop exit."}, ensure_ascii=False)


# ═══ SUPERVISOR LOOP ═════════════════════════════════════════════════════════


def supervisor_run(user_query: str) -> str:
    """Main Supervisor Loop.

    Empfaengt eine User-Frage, routet an Sub-Agents, sammelt Ergebnisse.

    Ablauf:
        1. User-Frage an Claude mit Routing-Tools
        2. Claude entscheidet welchen Agent er ruft (stop_reason == "tool_use")
        3. Sub-Agent wird ausgefuehrt, Ergebnis zurueck
        4. Claude bekommt Ergebnis: Nochmal routen oder antworten?
        5. stop_reason == "end_turn": Fertig, finale Antwort

    Args:
        user_query: Die User-Frage.

    Returns:
        Die finale Antwort des Supervisors.
    """
    print(f"\n{'=' * 60}")
    print(f"USER: {user_query}")
    print(f"{'=' * 60}")

    # Silver: Supervisor hat persistente History
    messages = agent_histories["supervisor"]
    messages.append({"role": "user", "content": user_query})

    for iteration in range(SUPERVISOR_MAX_ITERATIONS):
        print(f"\n--- Supervisor Iteration {iteration + 1}/{SUPERVISOR_MAX_ITERATIONS} ---")

        # Gold: Context Window Management
        working_messages = manage_context(messages)

        # API Call mit granularem Error Handling
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SUPERVISOR_PROMPT,
                tools=supervisor_tools,
                messages=working_messages,
            )
        except anthropic.AuthenticationError:
            print("FEHLER: API Key ungueltig (401 Unauthorized).")
            return "Error: API Key ungueltig."
        except anthropic.RateLimitError:
            print("FEHLER: Rate Limit erreicht (429). Bitte kurz warten.")
            return "Error: Rate Limit erreicht."
        except anthropic.APIConnectionError as exc:
            print(f"FEHLER: Keine Verbindung zur API: {exc}")
            return f"Error: Verbindungsfehler: {exc}"
        except anthropic.APIStatusError as exc:
            print(f"FEHLER: API-Fehler (Status {exc.status_code})")
            return f"Error: API-Fehler (Status {exc.status_code})"

        # Gold: Token Tracking
        track_tokens("supervisor", response)
        tokens = response.usage.input_tokens + response.usage.output_tokens
        print(f"Supervisor Stop: {response.stop_reason} | Tokens: {tokens}")

        # ── FALL 1: Claude ist fertig — finale Antwort ──
        if response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})

            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            return final_text

        # ── FALL 2: Claude will einen Agent aufrufen ──
        elif response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Routing to: {block.name}")
                    print(
                        f"  Task: {json.dumps(block.input, ensure_ascii=False)[:200]}"
                    )

                    # Gold: Agent mit Retry-Logik ausfuehren
                    result = execute_agent(block.name, block.input)

                    result_preview = result[:200] if result else "(empty)"
                    print(f"  Agent Result: {result_preview}...")

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            # Tool Results zurueck an den Supervisor
            messages.append({"role": "user", "content": tool_results})

        # ── FALL 3: Unerwarteter stop_reason ──
        else:
            logger.warning("Supervisor: Unerwarteter stop_reason: %s", response.stop_reason)
            return f"Error: Unerwarteter stop_reason: {response.stop_reason}"

    return "Supervisor: Max iterations reached."


# ═══ INTERACTIVE MODE ════════════════════════════════════════════════════════


def main() -> None:
    """Interaktiver Modus im Terminal."""
    agent_names = ["Research", "Analysis", "Writer"]
    print("=" * 60)
    print("  MULTI-AGENT RESEARCH SYSTEM")
    print(f"  Supervisor mit {len(supervisor_tools)} Routing-Tools")
    print(f"  Agents: {', '.join(agent_names)}")
    print("  Features: Chaining, Memory, Token Tracking, Error Recovery")
    print("-" * 60)
    print("  Befehle:")
    print("    quit     — System beenden")
    print("    tokens   — Token-Verbrauch anzeigen")
    print("    clear    — Alle Histories loeschen")
    print("=" * 60)

    while True:
        try:
            query = input("\nDeine Frage: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSystem beendet.")
            break

        if not query:
            continue

        if query.lower() in ("quit", "exit", "q"):
            print_token_summary()
            print("System beendet.")
            break

        if query.lower() == "tokens":
            print_token_summary()
            continue

        if query.lower() == "clear":
            for key in agent_histories:
                agent_histories[key].clear()
            reset_token_usage()
            print("Alle Histories und Token-Zaehler zurueckgesetzt.")
            continue

        # Supervisor ausfuehren
        answer = supervisor_run(query)

        print(f"\n{'=' * 60}")
        print(f"FINAL ANSWER:\n{answer}")
        print(f"{'=' * 60}")

        # Token Summary nach jeder Anfrage
        print_token_summary()


if __name__ == "__main__":
    main()
