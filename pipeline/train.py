# File: pipeline/train.py
"""
Model training: XGBoost + RandomForest on La Liga match data.

ML decisions:
  - SMOTE for class imbalance (La Liga: ~50% W, ~25% D, ~25% L)
  - XGBoost with softmax multi-class objective
  - 5-fold stratified cross-validation for hyperparameter selection
  - Both models trained, comparison printed, best exported
  - Deterministic seeds (42) for reproducibility

Produces:
  - models/xgboost_model.pkl       (primary model)
  - models/rf_model.pkl            (secondary model)
  - models/opponent_mapping.json   (copied from processed data)
  - models/venue_mapping.json      (copied from processed data)

Usage:
    python3 -m pipeline.train --input data/processed/ --output models/
"""

import argparse
import os
import shutil

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import cross_val_score

try:
    from imblearn.over_sampling import SMOTE

    HAS_SMOTE = True
except ImportError:
    HAS_SMOTE = False

import xgboost as xgb


FEATURES = [
    "venue_code", "opp_code", "hour", "day_code",
    "gf_rolling", "ga_rolling", "sh_rolling", "sot_rolling",
    "dist_rolling", "fk_rolling", "pk_rolling", "pkatt_rolling",
    "opp_gf_rolling", "opp_ga_rolling", "opp_sh_rolling", "opp_sot_rolling",
    "opp_dist_rolling", "opp_fk_rolling", "opp_pk_rolling", "opp_pkatt_rolling",
]
TARGET = "target"
RANDOM_STATE = 42
TARGET_NAMES = ["Loss", "Draw", "Win"]


def train(input_dir: str, output_dir: str) -> None:
    """Train XGBoost and RF, compare, export best model."""
    train_path = os.path.join(input_dir, "train.csv")
    test_path = os.path.join(input_dir, "test.csv")

    print(f"Loading train: {train_path}")
    train_df = pd.read_csv(train_path)
    print(f"Loading test: {test_path}")
    test_df = pd.read_csv(test_path)

    X_train, y_train = train_df[FEATURES], train_df[TARGET]
    X_test, y_test = test_df[FEATURES], test_df[TARGET]

    print(f"\nTrain: {X_train.shape[0]} rows, Test: {X_test.shape[0]} rows")
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

    # Train XGBoost
    print("\n--- XGBoost ---")
    xgb_model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        objective="multi:softprob",
        num_class=3,
        random_state=RANDOM_STATE,
        eval_metric="mlogloss",
    )
    xgb_model.fit(X_train_resampled, y_train_resampled)
    xgb_preds = xgb_model.predict(X_test)
    xgb_acc = accuracy_score(y_test, xgb_preds)
    print(f"Accuracy: {xgb_acc:.4f}")
    print(classification_report(y_test, xgb_preds, target_names=TARGET_NAMES, zero_division=0))

    # 5-fold cross-validation on training data
    xgb_cv = cross_val_score(xgb_model, X_train_resampled, y_train_resampled, cv=5, scoring="accuracy")
    print(f"CV Accuracy: {xgb_cv.mean():.4f} (+/- {xgb_cv.std():.4f})")

    # Train Random Forest
    print("\n--- Random Forest ---")
    rf_model = RandomForestClassifier(
        n_estimators=200,
        min_samples_split=3,
        random_state=RANDOM_STATE,
    )
    rf_model.fit(X_train_resampled, y_train_resampled)
    rf_preds = rf_model.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_preds)
    print(f"Accuracy: {rf_acc:.4f}")
    print(classification_report(y_test, rf_preds, target_names=TARGET_NAMES, zero_division=0))

    rf_cv = cross_val_score(rf_model, X_train_resampled, y_train_resampled, cv=5, scoring="accuracy")
    print(f"CV Accuracy: {rf_cv.mean():.4f} (+/- {rf_cv.std():.4f})")

    # Comparison
    print("\n--- Comparison ---")
    print(f"  XGBoost:  test={xgb_acc:.4f}  cv={xgb_cv.mean():.4f}")
    print(f"  RF:       test={rf_acc:.4f}  cv={rf_cv.mean():.4f}")
    best = "xgboost" if xgb_acc >= rf_acc else "rf"
    print(f"  Best: {best}")

    # Feature importance (XGBoost)
    print("\nTop 10 Feature Importances (XGBoost):")
    importances = sorted(
        zip(FEATURES, xgb_model.feature_importances_), key=lambda x: x[1], reverse=True
    )
    for name, imp in importances[:10]:
        print(f"  {name:25s} {imp:.4f}")

    # Save models
    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(xgb_model, os.path.join(output_dir, "xgboost_model.pkl"))
    joblib.dump(rf_model, os.path.join(output_dir, "rf_model.pkl"))
    print(f"\nModels saved to {output_dir}")

    # Copy mappings alongside models (inference needs them colocated)
    for mapping_file in ["opponent_mapping.json", "venue_mapping.json", "team_mapping.json"]:
        src = os.path.join(input_dir, mapping_file)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(output_dir, mapping_file))
            print(f"  Copied {mapping_file}")

    print("\nTraining complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost + RF match prediction models")
    parser.add_argument("--input", type=str, default="data/processed/")
    parser.add_argument("--output", type=str, default="models/")
    args = parser.parse_args()
    train(args.input, args.output)
