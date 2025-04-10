import argparse
import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Import SMOTE
try:
    from imblearn.over_sampling import SMOTE
    imblearn_installed = True
except ImportError:
    imblearn_installed = False
    # If imblearn isn't installed in the SageMaker environment, this will fail.
    # Ensure your SageMaker environment/container has imbalanced-learn installed.
    print("Error: imbalanced-learn library not found. SMOTE cannot be used.")
    # Optionally raise an error or exit if SMOTE is essential
    # raise ImportError("imbalanced-learn library required but not found.")


# Training entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Define command line arguments (reads environment variables set by SageMaker)
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR"))
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN"))
    parser.add_argument("--test", type=str, default=os.environ.get("SM_CHANNEL_TEST"))
    # Add any hyperparameters you might want to pass as arguments (optional)
    # parser.add_argument('--n-estimators', type=int, default=100)
    # parser.add_argument('--min-samples-split', type=int, default=3)

    args = parser.parse_args()

    print("Loading training and test data...")
    train_df = pd.read_csv(os.path.join(args.train, "train.csv"))
    test_df = pd.read_csv(os.path.join(args.test, "test.csv"))
    print(f"Training data shape: {train_df.shape}")
    print(f"Test data shape: {test_df.shape}")

    # --- Define Features (Updated: Excludes 'team') ---
    features = [
        'venue_code', 'opp_code', 'hour', 'day_code',
        'gf_rolling', 'ga_rolling', 'sh_rolling', 'sot_rolling', 'dist_rolling',
        'fk_rolling', 'pk_rolling', 'pkatt_rolling',
        'opp_gf_rolling', 'opp_ga_rolling', 'opp_sh_rolling', 'opp_sot_rolling',
        'opp_dist_rolling', 'opp_fk_rolling', 'opp_pk_rolling', 'opp_pkatt_rolling'
    ]
    target = "target"

    # Ensure features exist in loaded data
    features = [f for f in features if f in train_df.columns]
    print(f"Using {len(features)} features: {features}")

    X_train_orig, y_train = train_df[features], train_df[target]
    X_test, y_test = test_df[features], test_df[target]

    # --- Apply SMOTE (New Step) ---
    if imblearn_installed:
        print("\nApplying SMOTE to training data...")
        smote = SMOTE(random_state=2526) # Use consistent random state
        try:
            X_train, y_train = smote.fit_resample(X_train_orig, y_train) # Resample
            print(f"Training data shape after SMOTE: {X_train.shape}")
            print("SMOTE applied successfully.")
            print("Resampled training distribution:")
            print(y_train.value_counts(normalize=True) * 100)
        except Exception as e:
            print(f"Error during SMOTE: {e}")
            print("Proceeding with original training data. Check SMOTE requirements (e.g., samples per class).")
            X_train = X_train_orig # Fallback to original if SMOTE fails
    else:
        print("\nSkipping SMOTE as imbalanced-learn is not installed.")
        X_train = X_train_orig # Use original data if SMOTE not available


    # --- Define and Train Model (Updated Parameters) ---
    print("\nDefining and training RandomForestClassifier model...")
    model = RandomForestClassifier(
        n_estimators=100,       # Or use args.n_estimators if passed
        random_state=2526,
        min_samples_split=3     # Updated to match notebook
        # Add other parameters if needed
    )
    model.fit(X_train, y_train) # Train on potentially resampled data
    print("Model training complete.")

    # --- Save the Model ---
    # model_save_path = os.path.join(args.model_dir, "final_rm_rf_smote_model.joblib") # More descriptive name
    expected_model_filename = "randomforest_model.pkl" # Or .joblib if you prefer and can update inference code
    model_save_path = os.path.join(args.model_dir, expected_model_filename)
    print(f"\nSaving model to {model_save_path}...")
    joblib.dump(model, model_save_path)
    print("Model saved successfully.")

    # --- Evaluate the Model ---
    print("\nEvaluating model on test data...")
    y_pred = model.predict(X_test) # Evaluate on original test data

    print("\n--- Test Set Evaluation Results ---")
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, zero_division=0, labels=[0, 1, 2], target_names=['Loss', 'Draw', 'Win'])
    conf_matrix = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])

    print(f"Accuracy: {accuracy:.4f}")
    print("Classification Report:")
    print(report)
    print("Confusion Matrix:")
    print(conf_matrix)

    # You can also save metrics if needed, e.g., to a JSON file in SM_MODEL_DIR

    print("\nTraining script finished.")