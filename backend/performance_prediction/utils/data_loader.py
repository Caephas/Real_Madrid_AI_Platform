#Load the preprocessed data or trained model into other parts of the code.

import pandas as pd
import joblib

def load_preprocessed_data(file_path="../data/final_preprocessed_data.csv"):
    """
    Load preprocessed data from a CSV file.
    """
    return pd.read_csv(file_path)

def load_trained_model(model_path="../models/random_forest_model.pkl"):
    """
    Load a trained model from a file.
    """
    return joblib.load(model_path)