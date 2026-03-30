"""
utils/token_tracker.py — Token-Verbrauch Tracking pro Agent (Gold).

Trackt Input/Output Tokens und API-Calls pro Agent.
Berechnet Kosten-Schaetzung basierend auf Claude Sonnet Preisen.

Datum: 17.03.2026 | Sebastian
"""

from typing import Any

# ═══ TOKEN USAGE TRACKER ═════════════════════════════════════════════════════

token_usage: dict[str, dict[str, int]] = {
    "supervisor": {"input": 0, "output": 0, "calls": 0},
    "research": {"input": 0, "output": 0, "calls": 0},
    "analysis": {"input": 0, "output": 0, "calls": 0},
    "writer": {"input": 0, "output": 0, "calls": 0},
}


def track_tokens(agent_name: str, response: Any) -> None:
    """Tracked Token-Verbrauch pro Agent.

    Args:
        agent_name: Name des Agents (supervisor, research, analysis, writer)
        response: API Response mit usage.input_tokens und usage.output_tokens
    """
    if agent_name not in token_usage:
        token_usage[agent_name] = {"input": 0, "output": 0, "calls": 0}

    try:
        token_usage[agent_name]["input"] += response.usage.input_tokens
        token_usage[agent_name]["output"] += response.usage.output_tokens
        token_usage[agent_name]["calls"] += 1
    except AttributeError:
        pass  # Defensive: Falls response kein usage hat


def print_token_summary() -> None:
    """Zeigt Token-Verbrauch aller Agents mit Kosten-Schaetzung."""
    print(f"\n{'=' * 60}")
    print("TOKEN USAGE SUMMARY")
    print(f"{'=' * 60}")

    total_input = 0
    total_output = 0

    for agent, usage in token_usage.items():
        total = usage["input"] + usage["output"]
        total_input += usage["input"]
        total_output += usage["output"]
        if usage["calls"] > 0:
            print(
                f"  {agent:15} | Calls: {usage['calls']:2} | "
                f"Input: {usage['input']:6} | Output: {usage['output']:5} | "
                f"Total: {total:6}"
            )

    print(f"{'-' * 60}")
    grand_total = total_input + total_output
    print(
        f"  {'TOTAL':15} | "
        f"Input: {total_input:6} | Output: {total_output:5} | "
        f"Total: {grand_total:6}"
    )

    # Kosten-Schaetzung (Claude Sonnet Preise, Stand Maerz 2026)
    # Input: $3 / 1M tokens, Output: $15 / 1M tokens
    cost_input = (total_input / 1_000_000) * 3.0
    cost_output = (total_output / 1_000_000) * 15.0
    total_cost = cost_input + cost_output

    print(f"\n  Estimated cost: ${total_cost:.4f}")
    print(f"    Input:  ${cost_input:.4f}")
    print(f"    Output: ${cost_output:.4f}")
    print(f"{'=' * 60}")


def reset_token_usage() -> None:
    """Setzt alle Token-Zaehler zurueck."""
    for agent in token_usage:
        token_usage[agent] = {"input": 0, "output": 0, "calls": 0}


def get_token_summary() -> dict:
    """Gibt Token-Verbrauch als Dictionary zurueck (fuer wandb etc.)."""
    total_input = sum(u["input"] for u in token_usage.values())
    total_output = sum(u["output"] for u in token_usage.values())
    return {
        "per_agent": dict(token_usage),
        "total_input": total_input,
        "total_output": total_output,
        "total": total_input + total_output,
        "estimated_cost_usd": (total_input / 1_000_000) * 3.0
        + (total_output / 1_000_000) * 15.0,
    }
