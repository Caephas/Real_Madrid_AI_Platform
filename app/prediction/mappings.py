# File: app/prediction/mappings.py
"""Deterministic opponent/venue code mappings for inference.

These JSON files are produced by pipeline/clean.py and copied to models/ by pipeline/train.py.
They ensure the same numeric encoding used during training is applied at inference time.
"""

import json
from pathlib import Path

from app.config import settings

_opponent_mapping: dict[str, int] | None = None
_venue_mapping: dict[str, int] | None = None


def _load_json(filename: str) -> dict:
    path = Path(settings.model_dir) / filename
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found at {path}. Run `make pipeline` first.")
    with open(path) as f:
        return json.load(f)


def load_mappings() -> None:
    """Load all mapping files at startup. Called from app lifespan."""
    global _opponent_mapping, _venue_mapping
    _opponent_mapping = _load_json("opponent_mapping.json")
    _venue_mapping = _load_json("venue_mapping.json")


def get_opponent_code(opponent: str) -> int:
    """Map opponent name to numeric code. Raises ValueError if unknown."""
    if _opponent_mapping is None:
        raise RuntimeError("Mappings not loaded.")
    code = _opponent_mapping.get(opponent)
    if code is None:
        valid = ", ".join(sorted(_opponent_mapping.keys()))
        raise ValueError(f"Unknown opponent '{opponent}'. Valid opponents: {valid}")
    return code


def get_venue_code(venue: str) -> int:
    """Map venue ('Home'/'Away') to numeric code."""
    if _venue_mapping is None:
        raise RuntimeError("Mappings not loaded.")
    # Accept case-insensitive input
    normalized = venue.capitalize()
    code = _venue_mapping.get(normalized)
    if code is None:
        raise ValueError(f"Unknown venue '{venue}'. Must be 'Home' or 'Away'.")
    return code


def get_known_opponents() -> list[str]:
    """Return sorted list of valid opponent names."""
    if _opponent_mapping is None:
        return []
    return sorted(_opponent_mapping.keys())
