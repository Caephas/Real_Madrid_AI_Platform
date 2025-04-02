import boto3
import pandas as pd

# Initialize SageMaker runtime client
runtime = boto3.client("sagemaker-runtime", region_name="eu-west-1")

# Replace with your actual deployed endpoint name
endpoint = "sagemaker-scikit-learn-2025-04-02-12-28-03-049"

# Input DataFrame
sample = pd.DataFrame([{
    "venue_code": 1,
    "team": 4,
    "opp_code": 9,
    "hour": 20,
    "day_code": 6,
    "gf_rolling": 1.5,
    "ga_rolling": 0.8,
    "sh_rolling": 12.1,
    "sot_rolling": 5.3,
    "dist_rolling": 40.2,
    "fk_rolling": 2.1,
    "pk_rolling": 0.0,
    "pkatt_rolling": 0.1,
    "opp_gf_rolling": 1.0,
    "opp_ga_rolling": 1.3,
    "opp_sh_rolling": 10.5,
    "opp_sot_rolling": 4.0,
    "opp_dist_rolling": 38.0,
    "opp_fk_rolling": 1.9,
    "opp_pk_rolling": 0.0,
    "opp_pkatt_rolling": 0.1
}])

# Convert to JSON
payload = sample.to_json(orient="records")

# Send request to SageMaker endpoint
response = runtime.invoke_endpoint(
    EndpointName=endpoint,
    ContentType="application/json",
    Body=payload
)

# Print result
print("Prediction:", response['Body'].read().decode())