# File: app/prediction/router.py
"""POST /predict — match outcome prediction endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.prediction.features import build_feature_vector
from app.prediction.mappings import get_known_opponents
from app.prediction.model import get_model

router = APIRouter()


class PredictRequest(BaseModel):
    opponent: str = Field(..., description="Opponent team name, e.g. 'Barcelona'")
    venue: str = Field(..., description="'Home' or 'Away'")
    date: str = Field(..., description="Match date YYYY-MM-DD, e.g. '2025-04-13'")


class PredictResponse(BaseModel):
    win: float
    draw: float
    loss: float


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

    # Model target encoding: 0=Loss, 1=Draw, 2=Win
    return PredictResponse(
        loss=round(float(probabilities[0]), 4),
        draw=round(float(probabilities[1]), 4),
        win=round(float(probabilities[2]), 4),
    )


@router.get("/opponents")
def list_opponents():
    """Return sorted list of valid opponent names from training mappings."""
    return {"opponents": get_known_opponents()}


@router.get("/next-match")
def next_match():
    """Return the next upcoming Real Madrid La Liga fixture."""
    from app.fixtures import get_next_match
    result = get_next_match()
    if result is None:
        return {"message": "No upcoming fixtures — season is over"}
    return result


@router.get("/fixtures")
def remaining_fixtures():
    """Return all remaining Real Madrid La Liga fixtures."""
    from app.fixtures import get_remaining_fixtures
    return {"fixtures": get_remaining_fixtures()}
