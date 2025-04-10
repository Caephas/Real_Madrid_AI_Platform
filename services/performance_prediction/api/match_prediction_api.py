import boto3
import pandas as pd
import datetime

# --- Step 1 & 2: Get Match Info & Static Features ---
match_date_str = "2025-04-13" 
match_time_str = "15:15"
is_rm_home = False 
opponent_name = "Alavés"

match_date = pd.to_datetime(match_date_str)
hour_val = int(match_time_str.split(':')[0])
day_code_val = match_date.dayofweek
venue_code_val = 1 if is_rm_home else 0

opp_code_val = 0

# TODO #1:
# --- Step 3 & 4: Get Recent Data & Calculate Rolling Averages ---
# This requires external functions/data sources to get stats for last 5 games
# for both RM and Alavés BEFORE match_date_str

# TODO: --- Hypothetical Placeholder Values (REPLACE WITH ACTUAL CALCULATIONS) ---
rm_last_5_stats = {'gf': 2.2, 'ga': 0.8, 'sh': 15.0, 'sot': 6.1, 'dist': 17.5, 'fk': 0.4, 'pk': 0.2, 'pkatt': 0.2}
alaves_last_5_stats = {'gf': 0.8, 'ga': 1.4, 'sh': 9.5, 'sot': 3.2, 'dist': 19.1, 'fk': 0.2, 'pk': 0.0, 'pkatt': 0.0}
# --- End Placeholder Values ---

# --- Step 5: Assemble Payload ---
prediction_input = {
    "venue_code": venue_code_val,
    "opp_code": opp_code_val,
    "hour": hour_val,
    "day_code": day_code_val,
    "gf_rolling": rm_last_5_stats['gf'],
    "ga_rolling": rm_last_5_stats['ga'],
    "sh_rolling": rm_last_5_stats['sh'],
    "sot_rolling": rm_last_5_stats['sot'],
    "dist_rolling": rm_last_5_stats['dist'],
    "fk_rolling": rm_last_5_stats['fk'],
    "pk_rolling": rm_last_5_stats['pk'],
    "pkatt_rolling": rm_last_5_stats['pkatt'],
    "opp_gf_rolling": alaves_last_5_stats['gf'],
    "opp_ga_rolling": alaves_last_5_stats['ga'],
    "opp_sh_rolling": alaves_last_5_stats['sh'],
    "opp_sot_rolling": alaves_last_5_stats['sot'],
    "opp_dist_rolling": alaves_last_5_stats['dist'], 
    "opp_fk_rolling": alaves_last_5_stats['fk'],  
    "opp_pk_rolling": alaves_last_5_stats['pk'],
    "opp_pkatt_rolling": alaves_last_5_stats['pkatt']
}
# Verify features against the list used in training
training_features = [
    'venue_code', 'opp_code', 'hour', 'day_code', 'gf_rolling', 'ga_rolling',
    'sh_rolling', 'sot_rolling', 'dist_rolling', 'fk_rolling', 'pk_rolling',
    'pkatt_rolling', 'opp_gf_rolling', 'opp_ga_rolling', 'opp_sh_rolling',
    'opp_sot_rolling', 'opp_dist_rolling', 'opp_fk_rolling', 'opp_pk_rolling',
    'opp_pkatt_rolling'
] 

# Create DataFrame in correct order
input_df = pd.DataFrame([prediction_input], columns=training_features)


# --- Step 6: Format and Send to Endpoint ---
runtime = boto3.client("sagemaker-runtime", region_name="eu-west-1") 
endpoint = "sagemaker-scikit-learn-2025-04-10-14-56-48-770"

payload = input_df.to_json(orient="records")

response = runtime.invoke_endpoint(
    EndpointName=endpoint,
    ContentType="application/json",
    Body=payload
)

# Print result
print("Prediction Input Sent:")
print(payload)
print("\nPrediction Result:", response['Body'].read().decode())