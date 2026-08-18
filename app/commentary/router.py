# File: app/commentary/router.py
"""GET /commentary — live match commentary endpoint.
   GET /next-fixture — next scheduled match from API-Football.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.commentary.api_football import get_live_events_async, get_next_fixture
from app.commentary.generator import generate_match_summary

router = APIRouter()


class FixtureInfo(BaseModel):
    fixture_id: int
    home: str
    away: str
    score_home: int | None
    score_away: int | None
    status: str
    elapsed: int | None


class CommentaryItem(BaseModel):
    minute: int | str
    type: str
    text: str


class CommentaryResponse(BaseModel):
    fixture: FixtureInfo | None
    commentary: list[CommentaryItem]
    event_count: int


class NextFixtureResponse(BaseModel):
    fixture_id: int
    opponent: str
    venue: str
    date: str
    competition: str


@router.get("/commentary", response_model=CommentaryResponse)
async def live_commentary(
    team_id: int = Query(default=None, description="Team ID (defaults to Real Madrid)"),
):
    """Fetch live match events and generate commentary.

    Returns fixture info + commentary text for each event.
    If no live match found, returns empty commentary list.
    """
    events = await get_live_events_async(team_id)

    if not events:
        return CommentaryResponse(fixture=None, commentary=[], event_count=0)

    fixture_info = events[0]["fixture"]
    commentary = generate_match_summary(events)

    return CommentaryResponse(
        fixture=FixtureInfo(**fixture_info),
        commentary=[CommentaryItem(**c) for c in commentary],
        event_count=len(commentary),
    )


@router.get("/next-fixture", response_model=NextFixtureResponse | None)
def next_fixture():
    """Return the next scheduled Real Madrid match from API-Football.

    Returns null if API_FOOTBALL_KEY is not set or no fixture found.
    """
    result = get_next_fixture()
    if result is None:
        return None
    return NextFixtureResponse(**result)
