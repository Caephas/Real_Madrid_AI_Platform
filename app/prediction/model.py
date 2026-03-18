# File: app/prediction/model.py
"""Model loader: reads XGBoost/RF from the models/ volume mount.

Loaded once at startup via FastAPI lifespan, cached in module-level global.
No S3, no boto3. Just filesystem.
"""

from pathlib import Path

import joblib

from app.config import settings

_model = None


def load_model(model_name: str = "rf_model.pkl") -> object:
    """Load and cache the trained model from MODEL_DIR.

    Called once during app lifespan startup. Subsequent calls return the cached instance.
    Falls back to xgboost_model.pkl if the default is not found.
    """
    global _model
    path = Path(settings.model_dir) / model_name
    if not path.exists():
        # Try alternative model file
        alt = Path(settings.model_dir) / "xgboost_model.pkl"
        if alt.exists():
            path = alt
        else:
            raise FileNotFoundError(f"No model found in {settings.model_dir}. Run `make pipeline` first.")
    _model = joblib.load(path)
    return _model


def get_model() -> object:
    """Return the cached model. Raises if load_model() hasn't been called."""
    if _model is None:
        raise RuntimeError("Model not loaded. App lifespan should call load_model() at startup.")
    return _model
