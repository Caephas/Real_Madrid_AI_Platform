import os
import json
import joblib
import pandas as pd


LABELS = {0: "Lose", 1: "Draw", 2: "Win"}

def model_fn(model_dir):
    model_path = os.path.join(model_dir, "randomforest_model.pkl")
    return joblib.load(model_path)


def input_fn(request_body, request_content_type):
    if request_content_type == "application/json":
        data = json.loads(request_body)
        if isinstance(data, dict):
            data = [data]
        return pd.DataFrame(data)
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")


def predict_fn(input_data, model):
    proba = model.predict_proba(input_data)
    classes = model.classes_
    return [
        dict(zip([LABELS[c] for c in classes], map(float, row)))
        for row in proba
    ]


def output_fn(prediction, response_content_type):
    if response_content_type == "application/json":
        return json.dumps(prediction)
    else:
        raise ValueError(f"Unsupported content type: {response_content_type}")