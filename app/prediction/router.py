# File: app/prediction/router.py
"""Prediction endpoints: /predict, /predict/analysis, /opponents, /next-match, /fixtures."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.prediction.features import _get_team_rolling, build_feature_vector, compute_insights
from app.prediction.mappings import get_known_opponents
from app.prediction.model import get_model

router = APIRouter()
logger = logging.getLogger("app.prediction")

# Deterministic LLM analysis is expensive (tokens + latency) — cache per fixture.
_analysis_cache: dict = {}
_ANALYSIS_CACHE_TTL_SECONDS = 6 * 60 * 60


class PredictRequest(BaseModel):
    opponent: str = Field(..., description="Opponent team name, e.g. 'Barcelona'")
    venue: str = Field(..., description="'Home' or 'Away'")
    date: str = Field(..., description="Match date YYYY-MM-DD, e.g. '2025-04-13'")


class PredictResponse(BaseModel):
    win: float
    draw: float
    loss: float
    insights: list[str] = Field(
        default_factory=list, description="Why the model leans the way it does"
    )


class TeamForm(BaseModel):
    """Human-readable rolling stats for one team."""

    team: str
    goals_scored: float
    goals_conceded: float
    shots: float
    shots_on_target: float
    shot_distance: float


class AnalysisResponse(BaseModel):
    prediction: PredictResponse
    real_madrid_form: TeamForm
    opponent_form: TeamForm
    key_factors: list[str]
    ai_narrative: str


class FixtureInfo(BaseModel):
    matchday: int
    date: str
    opponent: str
    venue: str
    kickoff: str | None = None
    api_source: bool = False
    status: str | None = None
    result: str | None = None
    score: str | None = None


class SeasonResponse(BaseModel):
    season: str
    competition: str
    start_date: str | None = None
    end_date: str | None = None
    next_match: FixtureInfo | None = None
    fixtures: list[FixtureInfo]


@router.post("/predict", response_model=PredictResponse)
def predict_match(req: PredictRequest, db: Session = Depends(get_db)):
    """Predict Win/Draw/Loss probabilities for a Real Madrid match."""
    try:
        features = build_feature_vector(
            opponent=req.opponent,
            venue=req.venue,
            date=req.date,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    model = get_model()
    probabilities = model.predict_proba(features)[0]

    return PredictResponse(
        loss=round(float(probabilities[0]), 4),
        draw=round(float(probabilities[1]), 4),
        win=round(float(probabilities[2]), 4),
        insights=compute_insights(features.iloc[0].to_dict(), req.opponent, req.venue),
    )


@router.post("/predict/analysis", response_model=AnalysisResponse)
def predict_with_analysis(req: PredictRequest, db: Session = Depends(get_db)):
    """Predict + generate AI-powered match analysis with team form comparison."""
    cache_key = (req.opponent, req.venue, req.date)
    cached = _analysis_cache.get(cache_key)
    if cached and time.time() - cached[0] < _ANALYSIS_CACHE_TTL_SECONDS:
        return cached[1]

    # Run prediction
    try:
        features = build_feature_vector(
            opponent=req.opponent,
            venue=req.venue,
            date=req.date,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    model = get_model()
    probabilities = model.predict_proba(features)[0]
    prediction = PredictResponse(
        loss=round(float(probabilities[0]), 4),
        draw=round(float(probabilities[1]), 4),
        win=round(float(probabilities[2]), 4),
        insights=compute_insights(features.iloc[0].to_dict(), req.opponent, req.venue),
    )

    # Get raw rolling stats for both teams
    rm_stats = _get_team_rolling(db, "Real Madrid")
    opp_stats = _get_team_rolling(db, req.opponent)

    rm_form = TeamForm(
        team="Real Madrid",
        goals_scored=round(rm_stats["gf_rolling"], 2),
        goals_conceded=round(rm_stats["ga_rolling"], 2),
        shots=round(rm_stats["sh_rolling"], 1),
        shots_on_target=round(rm_stats["sot_rolling"], 1),
        shot_distance=round(rm_stats["dist_rolling"], 1),
    )
    opp_form = TeamForm(
        team=req.opponent,
        goals_scored=round(opp_stats["gf_rolling"], 2),
        goals_conceded=round(opp_stats["ga_rolling"], 2),
        shots=round(opp_stats["sh_rolling"], 1),
        shots_on_target=round(opp_stats["sot_rolling"], 1),
        shot_distance=round(opp_stats["dist_rolling"], 1),
    )

    # Derive key factors from stats comparison
    key_factors = _derive_key_factors(rm_stats, opp_stats, req.opponent, req.venue)

    # Generate LLM narrative
    ai_narrative = _generate_narrative(
        prediction, rm_form, opp_form, key_factors, req.venue, req.date
    )

    response = AnalysisResponse(
        prediction=prediction,
        real_madrid_form=rm_form,
        opponent_form=opp_form,
        key_factors=key_factors,
        ai_narrative=ai_narrative,
    )
    _analysis_cache[cache_key] = (time.time(), response)
    return response


def _derive_key_factors(rm: dict, opp: dict, opponent: str, venue: str) -> list[str]:
    """Extract top insights from the stats comparison."""
    factors = []

    # Scoring comparison
    if rm["gf_rolling"] > opp["gf_rolling"] + 0.3:
        factors.append(
            f"Real Madrid are outscoring {opponent} ({rm['gf_rolling']:.1f} vs {opp['gf_rolling']:.1f} goals/game)"
        )
    elif opp["gf_rolling"] > rm["gf_rolling"] + 0.3:
        factors.append(
            f"{opponent} are outscoring Real Madrid ({opp['gf_rolling']:.1f} vs {rm['gf_rolling']:.1f} goals/game)"
        )

    # Defensive comparison
    if rm["ga_rolling"] < opp["ga_rolling"] - 0.3:
        factors.append(
            f"Real Madrid have the tighter defense ({rm['ga_rolling']:.1f} vs {opp['ga_rolling']:.1f} conceded/game)"
        )
    elif opp["ga_rolling"] < rm["ga_rolling"] - 0.3:
        factors.append(
            f"{opponent} have the tighter defense ({opp['ga_rolling']:.1f} vs {rm['ga_rolling']:.1f} conceded/game)"
        )

    # Shot efficiency
    rm_eff = rm["sot_rolling"] / max(rm["sh_rolling"], 1)
    opp_eff = opp["sot_rolling"] / max(opp["sh_rolling"], 1)
    if rm_eff > opp_eff + 0.05:
        factors.append(
            f"Real Madrid are more clinical ({rm_eff:.0%} shot accuracy vs {opp_eff:.0%})"
        )
    elif opp_eff > rm_eff + 0.05:
        factors.append(
            f"{opponent} are more clinical ({opp_eff:.0%} shot accuracy vs {rm_eff:.0%})"
        )

    # Shot volume
    if rm["sh_rolling"] > opp["sh_rolling"] + 2:
        factors.append(
            f"Real Madrid create more chances ({rm['sh_rolling']:.0f} vs {opp['sh_rolling']:.0f} shots/game)"
        )
    elif opp["sh_rolling"] > rm["sh_rolling"] + 2:
        factors.append(
            f"{opponent} create more chances ({opp['sh_rolling']:.0f} vs {rm['sh_rolling']:.0f} shots/game)"
        )

    # Home/away
    if venue == "Home":
        factors.append("Home advantage at the Bernabéu")
    else:
        factors.append("Away fixture — historically harder for Real Madrid")

    return factors[:5]


def _generate_narrative(
    pred: PredictResponse,
    rm: TeamForm,
    opp: TeamForm,
    factors: list[str],
    venue: str,
    date: str,
) -> str:
    """Use the LLM to generate a tactical match analysis narrative."""
    try:
        from app.chatbot.llm import create_provider

        prompt = f"""You are a veteran La Liga tactical analyst with 25 years of experience covering Spanish football. You have deep knowledge of every La Liga club's philosophy, playing style, historical rivalries, and tactical tendencies. You understand Real Madrid's DNA — their Bernabéu mentality, their big-game pedigree, and how they perform under pressure in derbies and clasicos.

You are given an ML model's match prediction and both teams' recent form. Write a sharp, professional tactical analysis (2 paragraphs, under 150 words) grounded in your knowledge of these specific teams and La Liga football.

Match: Real Madrid ({venue}) vs {opp.team} — {date}
Prediction: Win {pred.win:.0%} | Draw {pred.draw:.0%} | Loss {pred.loss:.0%}

Real Madrid (last 5 La Liga games): {rm.goals_scored} goals scored, {rm.goals_conceded} conceded, {rm.shots} shots ({rm.shots_on_target} on target) per game.
{opp.team} (last 5 La Liga games): {opp.goals_scored} goals scored, {opp.goals_conceded} conceded, {opp.shots} shots ({opp.shots_on_target} on target) per game.

Key statistical factors: {'; '.join(factors)}

Analyze why these probabilities make sense given the stats and what you know about these teams in La Liga. End with a predicted scoreline. No markdown. No bullet points. English only."""

        provider = create_provider()
        response = ""
        for attempt in range(2):
            response = provider.generate([{"role": "user", "content": prompt}])
            if response.strip():
                break
            # Reasoning-heavy models occasionally emit an empty final message.
            prompt = f"{prompt}\n\nYour previous response was empty. Write the analysis now."
        return response.strip()
    except Exception as e:
        logger.warning("LLM analysis generation failed: %s", e)
        return "AI analysis unavailable — LLM not responding."


@router.get("/opponents")
def list_opponents():
    """Return sorted list of valid opponent names from training mappings."""
    return {"opponents": get_known_opponents()}


@router.get("/next-match", response_model=FixtureInfo | None)
def next_match():
    """Return the next upcoming Real Madrid La Liga fixture."""
    from app.fixtures import get_next_match

    return get_next_match()


@router.get("/fixtures", response_model=dict)
def remaining_fixtures():
    """Return all remaining Real Madrid La Liga fixtures."""
    from app.fixtures import get_remaining_fixtures

    return {"fixtures": get_remaining_fixtures()}


@router.get("/season", response_model=SeasonResponse)
def season_info():
    """Return current-season metadata, next match, and the full fixture list."""
    from app.fixtures import get_season_info

    return get_season_info()


@router.get("/results", response_model=dict)
def recent_results(limit: int = Query(5, ge=1, le=10)):
    """Return recent finished Real Madrid matches with scores."""
    from app.fixtures import get_recent_results

    return {"results": get_recent_results(limit=limit)}


@router.get("/standings", response_model=dict)
def standings(season: int | None = Query(None, description="Season start year (default: latest)")):
    """League table for a season: position, W/D/L, points, last-5 form."""
    from app.history_data import available_seasons, get_standings

    if season is None:
        seasons = available_seasons()
        season = seasons[-1] if seasons else None
    return {
        "season": season,
        "available_seasons": available_seasons(),
        "standings": get_standings(season) if season else [],
    }


@router.get("/form", response_model=dict)
def team_form(
    team: str = Query(..., description="Team name, e.g. 'Real Madrid'"),
    season: int | None = Query(None),
    limit: int = Query(5, ge=1, le=10),
):
    """Recent results for a team as W/D/L, most recent first."""
    from app.history_data import get_form

    return {"team": team, "form": get_form(team, season=season, limit=limit)}


@router.get("/history", response_model=dict)
def season_history(
    season: int | None = Query(None, description="Season start year (default: latest)"),
):
    """Real Madrid's matches for a season."""
    from app.history_data import available_seasons, get_history

    if season is None:
        seasons = available_seasons()
        season = seasons[-1] if seasons else None
    return {
        "season": season,
        "available_seasons": available_seasons(),
        "matches": get_history(season) if season else [],
    }


@router.get("/h2h", response_model=dict)
def head_to_head(opponent: str = Query(...)):
    """Head-to-head record between Real Madrid and an opponent."""
    from app.history_data import get_h2h

    return get_h2h(opponent)
