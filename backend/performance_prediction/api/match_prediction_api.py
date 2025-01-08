from fastapi import FastAPI, HTTPException
import pandas as pd
import os
import joblib

# Dynamically calculate the absolute path to the model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../models/randomforest_model.pkl")

# If feature names are not explicitly saved, you can define them manually or load them during model training
FEATURE_NAMES_PATH = os.path.join(os.path.dirname(__file__), "../models/model_features.pkl")

# Load the trained model
try:
    model = joblib.load(MODEL_PATH)
except FileNotFoundError:
    raise RuntimeError(f"Trained model not found at path: {MODEL_PATH}")

# Load feature names or fallback to extracting them from the model
if os.path.exists(FEATURE_NAMES_PATH):
    feature_names = joblib.load(FEATURE_NAMES_PATH)
else:
    # If feature names are not saved, extract them from the model (works for tree-based models like RandomForest)
    feature_names = model.feature_names_in_.tolist() if hasattr(model, "feature_names_in_") else None
    if feature_names is None:
        raise RuntimeError("Feature names could not be loaded or inferred. Ensure they are saved during training.")

# Initialize FastAPI app
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Performance Prediction API is running!"}

@app.post("/prediction/match")
def predict_match(features: dict):
    """
    Predict the match outcome based on input features.
    Input should be a JSON object with all required features.
    """
    try:
        # Convert input to DataFrame
        input_data = pd.DataFrame([features])

        # Ensure input data matches training features
        if feature_names is not None:
            input_data = input_data.reindex(columns=feature_names, fill_value=0)

        # Predict match result
        prediction = model.predict(input_data)[0]  # Single prediction
        prediction = int(prediction)  # Convert numpy.int64 to Python int

        # Predict probabilities
        probabilities = model.predict_proba(input_data)[0]  # Probabilities for each class

        # Format probabilities into a dictionary
        outcome_probabilities = {
            "Class 0 (Loss)": f"{probabilities[0] * 100:.2f}%",
            "Class 1 (Draw)": f"{probabilities[1] * 100:.2f}%",
            "Class 2 (Win)": f"{probabilities[2] * 100:.2f}%"
        }

        # Determine the most likely outcome
        outcome_mapping = {0: "Loss", 1: "Draw", 2: "Win"}
        most_likely_outcome = outcome_mapping.get(prediction, "Unknown")

        return {
            "most_likely_outcome": most_likely_outcome,
            "class_probabilities": outcome_probabilities
        }
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required feature: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))