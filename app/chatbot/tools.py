# File: app/chatbot/tools.py
"""Tool definitions the agent can call. Each tool wraps an existing service endpoint.

The agent loop parses tool-call JSON from the LLM and dispatches here.
"""

import logging
from typing import Callable

from sqlalchemy.orm import Session

from app.commentary.api_football import get_live_events
from app.commentary.generator import generate_match_summary
from app.content.crud import get_articles
from app.prediction.features import build_feature_vector
from app.prediction.model import get_model

logger = logging.getLogger("app.chatbot")


def tool_predict_match(args: dict, db: Session) -> str:
    """Call the prediction service. Returns W/D/L probabilities as text."""
    opponent = args.get("opponent", "")
    venue = args.get("venue", "Home")
    date = args.get("date", "")

    if not opponent or not date:
        return "I need both an opponent name and a match date to make a prediction."

    try:
        features = build_feature_vector(opponent=opponent, venue=venue, date=date, db=db)
        model = get_model()
        probs = model.predict_proba(features)[0]

        # 0=Loss, 1=Draw, 2=Win
        return (
            f"Prediction for Real Madrid vs {opponent} ({venue}, {date}):\n"
            f"  Win:  {probs[2]*100:.1f}%\n"
            f"  Draw: {probs[1]*100:.1f}%\n"
            f"  Loss: {probs[0]*100:.1f}%"
        )
    except ValueError as e:
        return f"Prediction error: {e}"
    except RuntimeError as e:
        return f"Model not ready: {e}"


def tool_get_commentary(args: dict, db: Session) -> str:
    """Fetch live match commentary."""
    events = get_live_events()
    if not events:
        return "No live Real Madrid match found right now."

    fixture = events[0]["fixture"]
    commentary = generate_match_summary(events)
    lines = [f"Live: {fixture['home']} {fixture['score_home']}-{fixture['score_away']} {fixture['away']}"]
    lines.append(f"Status: {fixture['status']} ({fixture['elapsed']}')")
    lines.append("")
    for c in commentary[-10:]:  # Last 10 events
        lines.append(c["text"])

    return "\n".join(lines)


def tool_get_articles(args: dict, db: Session) -> str:
    """Fetch latest news articles."""
    limit = min(args.get("limit", 5), 10)

    articles = get_articles(db, limit=limit)
    if not articles:
        return "No articles found in the database."

    lines = []
    for a in articles:
        lines.append(f"[{a.category}] {a.title}")
        if a.content:
            lines.append(f"  Summary: {a.content[:150]}")
        lines.append(f"  Published: {a.published}")
    return "\n".join(lines)


# Registry: tool name → handler function
TOOLS: dict[str, Callable] = {
    "predict_match": tool_predict_match,
    "get_commentary": tool_get_commentary,
    "get_articles": tool_get_articles,
}
