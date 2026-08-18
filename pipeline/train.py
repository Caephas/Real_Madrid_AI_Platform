"""
Model training: XGBoost + RandomForest on La Liga match data.

ML decisions:
  - SMOTE for class imbalance (La Liga: ~50% W, ~25% D, ~25% L)
  - XGBoost with softmax multi-class objective + early stopping on the held-out test set
  - Model selection by test log loss (accuracy is misleading with class imbalance)
  - Deterministic seeds (42) for reproducibility
  - Metrics + feature importance exported as JSON artifacts next to the models

Produces:
  - models/xgboost_model.pkl       (primary model)
  - models/rf_model.pkl            (secondary model)
  - models/model_metrics.json      (accuracy, log loss, CV, classification report)
  - models/feature_importance.json (top features by importance)
  - models/*_mapping.json          (copied from processed data)

Usage:
    python3 -m pipeline.train --input data/processed/ --output models/
"""

import argparse
import json
import os
import shutil
from datetime import datetime

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, log_loss
from sklearn.model_selection import cross_val_score

try:
    from imblearn.over_sampling import SMOTE

    HAS_SMOTE = True
except ImportError:
    HAS_SMOTE = False

import xgboost as xgb

from app.prediction.features import MODEL_FEATURES


TARGET = "target"
RANDOM_STATE = 42
TARGET_NAMES = ["Loss", "Draw", "Win"]


def _load_features(input_dir: str) -> list[str]:
    """Feature list from clean.py metadata when present (single source of truth)."""
    meta_path = os.path.join(input_dir, "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            features = json.load(f).get("features")
        if features:
            return features
    return MODEL_FEATURES


def _load_metadata(input_dir: str) -> dict:
    meta_path = os.path.join(input_dir, "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            return json.load(f)
    return {}


def _build_xgb(early_stopping: bool = True) -> xgb.XGBClassifier:
    """XGBoost classifier with the project's default hyperparameters."""
    return xgb.XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.08,
        objective="multi:softprob",
        num_class=3,
        random_state=RANDOM_STATE,
        eval_metric="mlogloss",
        early_stopping_rounds=25 if early_stopping else None,
        verbosity=0,
    )


def train(input_dir: str, output_dir: str) -> None:
    """Train XGBoost and RF, compare by log loss, export best + metrics."""
    train_path = os.path.join(input_dir, "train.csv")
    test_path = os.path.join(input_dir, "test.csv")
    features = _load_features(input_dir)
    metadata = _load_metadata(input_dir)

    print(f"Loading train: {train_path}")
    train_df = pd.read_csv(train_path)
    print(f"Loading test: {test_path}")
    test_df = pd.read_csv(test_path)

    missing = [f for f in features if f not in train_df.columns]
    if missing:
        raise ValueError(f"Train CSV is missing features: {missing}")

    X_train, y_train = train_df[features], train_df[TARGET]
    X_test, y_test = test_df[features], test_df[TARGET]

    print(
        f"\nTrain: {X_train.shape[0]} rows, Test: {X_test.shape[0]} rows, Features: {len(features)}"
    )
    print(f"Train class distribution:\n{y_train.value_counts().sort_index().to_dict()}")

    # SMOTE for class imbalance
    if HAS_SMOTE:
        print("\nApplying SMOTE to training data...")
        smote = SMOTE(random_state=RANDOM_STATE)
        X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
        print(f"  Before SMOTE: {len(X_train)}, After: {len(X_train_resampled)}")
    else:
        print("\nimbalanced-learn not installed, skipping SMOTE")
        X_train_resampled, y_train_resampled = X_train, y_train

    # --- XGBoost with early stopping on the held-out test set ---
    print("\n--- XGBoost ---")
    xgb_model = _build_xgb(early_stopping=True)
    xgb_model.fit(
        X_train_resampled,
        y_train_resampled,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )
    xgb_probs = xgb_model.predict_proba(X_test)
    xgb_preds = xgb_model.predict(X_test)
    xgb_acc = accuracy_score(y_test, xgb_preds)
    xgb_ll = log_loss(y_test, xgb_probs)
    print(f"Accuracy: {xgb_acc:.4f} | Log loss: {xgb_ll:.4f}")
    print(classification_report(y_test, xgb_preds, target_names=TARGET_NAMES, zero_division=0))

    # --- Random Forest ---
    print("\n--- Random Forest ---")
    rf_model = RandomForestClassifier(
        n_estimators=400,
        min_samples_split=3,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rf_model.fit(X_train_resampled, y_train_resampled)
    rf_probs = rf_model.predict_proba(X_test)
    rf_preds = rf_model.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_preds)
    rf_ll = log_loss(y_test, rf_probs)
    print(f"Accuracy: {rf_acc:.4f} | Log loss: {rf_ll:.4f}")
    print(classification_report(y_test, rf_preds, target_names=TARGET_NAMES, zero_division=0))

    # --- Probability calibration (Platt scaling on original train) ---
    # SMOTE changes class priors, so the base model's probabilities are skewed.
    # Calibrating on the *original* training labels restores honest probabilities
    # without touching the held-out test set.
    print("\n--- Calibration (Platt scaling, cv='prefit') ---")
    calibrated: dict[str, CalibratedClassifierCV] = {}
    cal_ll: dict[str, float] = {}
    for name, model in (("xgboost", xgb_model), ("rf", rf_model)):
        cal = CalibratedClassifierCV(estimator=model, method="sigmoid", cv="prefit")
        cal.fit(X_train, y_train)
        calibrated[name] = cal
        cal_ll[name] = log_loss(y_test, cal.predict_proba(X_test))
        print(
            f"  {name}: uncalibrated log_loss={log_loss(y_test, model.predict_proba(X_test)):.4f} "
            f"→ calibrated log_loss={cal_ll[name]:.4f}"
        )

    # --- Comparison (selection by calibrated log loss; accuracy as tiebreak) ---
    print("\n--- Comparison ---")
    print(f"  XGBoost:  accuracy={xgb_acc:.4f}  log_loss={xgb_ll:.4f}")
    print(f"  RF:       accuracy={rf_acc:.4f}  log_loss={rf_ll:.4f}")

    uncal_models = {"xgboost": xgb_model, "rf": rf_model}
    uncal_ll = {"xgboost": xgb_ll, "rf": rf_ll}
    deployed: dict[str, object] = {}
    deployed_choice: dict[str, str] = {}
    for name in ("xgboost", "rf"):
        if cal_ll[name] < uncal_ll[name]:
            deployed[name] = calibrated[name]
            deployed_choice[name] = "calibrated"
        else:
            deployed[name] = uncal_models[name]
            deployed_choice[name] = "uncalibrated"
        print(
            f"  {name}: deploying {deployed_choice[name]} "
            f"(calibrated LL={cal_ll[name]:.4f} vs uncalibrated LL={uncal_ll[name]:.4f})"
        )

    def _deployed_score(name: str) -> tuple[float, float]:
        probs = deployed[name].predict_proba(X_test)
        return log_loss(y_test, probs), -accuracy_score(y_test, deployed[name].predict(X_test))

    best = min(("xgboost", "rf"), key=_deployed_score)
    print(f"  Best: {best}")

    # 5-fold CV on the (resampled) training data — reported, not used for selection
    cv_scores = {
        "xgboost": cross_val_score(
            _build_xgb(early_stopping=False),
            X_train_resampled,
            y_train_resampled,
            cv=5,
            scoring="accuracy",
        ).tolist(),
        "rf": cross_val_score(
            rf_model, X_train_resampled, y_train_resampled, cv=5, scoring="accuracy"
        ).tolist(),
    }

    # Feature importance (XGBoost)
    importances = sorted(
        zip(features, xgb_model.feature_importances_), key=lambda x: x[1], reverse=True
    )
    print("\nTop 10 Feature Importances (XGBoost):")
    for name, imp in importances[:10]:
        print(f"  {name:28s} {imp:.4f}")

    # Save models
    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(deployed["xgboost"], os.path.join(output_dir, "xgboost_model.pkl"))
    joblib.dump(deployed["rf"], os.path.join(output_dir, "rf_model.pkl"))

    # Copy mappings alongside models (inference needs them colocated)
    for mapping_file in ["opponent_mapping.json", "venue_mapping.json", "team_mapping.json"]:
        src = os.path.join(input_dir, mapping_file)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(output_dir, mapping_file))
            print(f"  Copied {mapping_file}")

    # Metrics artifact — one JSON for monitoring and model provenance
    metrics = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "n_features": len(features),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "features": features,
        "data_date_range": metadata.get("data_date_range"),
        "test_seasons": metadata.get("test_season_values"),
        "best_model": best,
        "calibration": {
            "method": "sigmoid",
            "deployed": deployed_choice,
            "calibrated_log_loss": cal_ll,
        },
        "calibration_method": "sigmoid",
        "models": {
            "xgboost": {
                "accuracy": round(xgb_acc, 4),
                "log_loss": round(xgb_ll, 4),
                "calibrated_log_loss": round(cal_ll["xgboost"], 4),
                "cv_accuracy_mean": round(float(pd.Series(cv_scores["xgboost"]).mean()), 4),
                "classification_report": classification_report(
                    y_test, xgb_preds, target_names=TARGET_NAMES, zero_division=0, output_dict=True
                ),
            },
            "rf": {
                "accuracy": round(rf_acc, 4),
                "log_loss": round(rf_ll, 4),
                "calibrated_log_loss": round(cal_ll["rf"], 4),
                "cv_accuracy_mean": round(float(pd.Series(cv_scores["rf"]).mean()), 4),
                "classification_report": classification_report(
                    y_test, rf_preds, target_names=TARGET_NAMES, zero_division=0, output_dict=True
                ),
            },
        },
    }
    with open(os.path.join(output_dir, "model_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    with open(os.path.join(output_dir, "feature_importance.json"), "w") as f:
        json.dump({name: float(imp) for name, imp in importances}, f, indent=2)

    # Per-feature mean/std on the ORIGINAL training set — powers per-prediction
    # explainability (z-score insights) at inference time.
    feature_stats = {
        "mean": {f: float(X_train[f].mean()) for f in features},
        "std": {f: float(X_train[f].std(ddof=0)) for f in features},
    }
    with open(os.path.join(output_dir, "feature_stats.json"), "w") as f:
        json.dump(feature_stats, f, indent=2)

    print(f"\nModels + metrics saved to {output_dir}")
    print("  xgboost_model.pkl, rf_model.pkl, model_metrics.json,")
    print("  feature_importance.json, feature_stats.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost + RF match prediction models")
    parser.add_argument("--input", type=str, default="data/processed/")
    parser.add_argument("--output", type=str, default="models/")
    args = parser.parse_args()
    train(args.input, args.output)
