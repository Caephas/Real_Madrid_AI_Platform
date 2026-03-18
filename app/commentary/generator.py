# File: app/commentary/generator.py
"""Commentary text generation from API-Football event objects.

Template-based — no LLM needed. Produces human-readable strings for each event type.
"""


def generate_commentary(event: dict) -> str:
    """Convert an API-Football event dict into a commentary string.

    Event types: Goal, Card, subst, Var. Each has a distinct template.
    """
    event_type = event.get("type", "")
    minute = event.get("time", {}).get("elapsed", "?")
    player = event.get("player", {}).get("name", "Unknown")
    detail = event.get("detail", "")

    if event_type == "Goal":
        if detail == "Own Goal":
            return f"{minute}' OWN GOAL! {player} puts the ball into his own net!"
        if detail == "Penalty":
            return f"{minute}' GOAL! {player} converts the penalty!"
        return f"{minute}' GOAL! {player} scores!"

    if event_type == "Card":
        color = "Yellow" if "Yellow" in detail else "Red"
        return f"{minute}' {color} card shown to {player}."

    if event_type == "subst":
        player_out = event.get("assist", {}).get("name", "Unknown")
        return f"{minute}' Substitution: {player} comes on for {player_out}."

    if event_type == "Var":
        return f"{minute}' VAR Review: {detail} involving {player}."

    return f"{minute}' Match event: {event_type} — {player}."


def generate_match_summary(events: list[dict]) -> list[dict]:
    """Generate commentary for a list of events. Returns list of {minute, type, text}."""
    return [
        {
            "minute": e.get("event", e).get("time", {}).get("elapsed", "?"),
            "type": e.get("event", e).get("type", "Unknown"),
            "text": generate_commentary(e.get("event", e)),
        }
        for e in events
    ]
