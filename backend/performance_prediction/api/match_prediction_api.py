from fastapi import FastAPI, HTTPException
from backend.performance_prediction.utils.data_loader import load_trained_model
import pandas as pd
import os
import joblib

# Dynamically calculate the absolute path to the model and feature names
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../models/random_forest_model.pkl")
FEATURE_NAMES_PATH = os.path.join(os.path.dirname(__file__), "../models/model_features.pkl")

# Load the trained model and feature names
model = load_trained_model(MODEL_PATH)
feature_names = joblib.load(FEATURE_NAMES_PATH)

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

        # Reindex input data to match the training feature names
        input_data = input_data.reindex(columns=feature_names, fill_value=0)

        # Predict match result
        prediction = model.predict(input_data)[0]  # Prediction is likely a numpy.int64

        # Convert numpy.int64 to Python int
        prediction = int(prediction)

        # Map prediction to an outcome
        outcome = {1: "Win", 0: "Loss", 2: "Draw"}.get(prediction, "Unknown")

        return {
            "prediction": prediction,
            "outcome": outcome
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))