import pandas as pd
import numpy as np # Needed for dtypes check
import os
import sagemaker
from dotenv import load_dotenv

# --- Load Environment Variables ---
try:
    load_dotenv(dotenv_path="services/performance_prediction/.env")
    bucket = os.environ["S3_BUCKET"]
except Exception as e:
    print(f"Error loading .env or S3_BUCKET: {e}. Please ensure .env file exists and S3_BUCKET is set.")
    exit() # Exit if configuration is missing

print("Starting data preparation and splitting...")

# --- Define Rolling Average Function ---
def rolling_average(group, cols, new_cols):
    group = group.sort_values('date')
    rolling_stats = group[cols].rolling(5, closed='left').mean()
    for col, new_col in zip(cols, new_cols):
        group[new_col] = rolling_stats[col]
    # Drop only NaNs created by rolling average calculation itself
    group = group.dropna(subset=new_cols)
    return group

# --- 1. Load Raw Data ---
try:
    matches_raw = pd.read_csv("data/combined_la_liga.csv", parse_dates=['date'])
    print(f"Raw data loaded. Shape: {matches_raw.shape}")
except FileNotFoundError:
    raise FileNotFoundError("Error: 'data/combined_la_liga.csv' not found.")

# --- 2. Preprocessing & Feature Engineering (All Teams) ---
matches = matches_raw.copy()
matches.reset_index(inplace=True)
matches.rename(columns={'index': 'original_index'}, inplace=True, errors='ignore')

# Ensure date is datetime
if not pd.api.types.is_datetime64_any_dtype(matches['date']):
     matches['date'] = pd.to_datetime(matches['date'])

# Create basic features
matches["venue_code"] = matches["venue"].astype('category').cat.codes
matches['opp_code'] = matches['opponent'].astype('category').cat.codes
matches['team_code'] = matches['team'].astype('category').cat.codes # Use team_code
matches['hour'] = matches['time'].str.replace(':.+','',regex=True).astype('int')
matches['day_code'] = matches['date'].dt.dayofweek
matches['target'] = matches['result'].map({'W': 2, 'D': 1, 'L': 0})

print("Basic features created.")

# Calculate rolling averages
cols_to_roll = ['gf', 'ga', 'sh', 'sot', 'dist', 'fk', 'pk', 'pkatt']
new_rolling_cols = [f'{c}_rolling' for c in cols_to_roll]

print("Calculating team rolling averages...")
# Apply rolling average using team_code
matches_rolling_base = matches.groupby('team_code').apply(lambda x: rolling_average(x, cols_to_roll, new_rolling_cols))
# Check if groupby resulted in MultiIndex, if so, reset
if isinstance(matches_rolling_base.index, pd.MultiIndex):
    matches_rolling_base = matches_rolling_base.reset_index(level=0, drop=True) # Drop the group key level
matches_rolling_base = matches_rolling_base.reset_index() # Ensure a flat index if needed, keeping original index if present

print("Merging opponent rolling averages...")
# Merge opponent stats
opponent_rolling_stats = matches_rolling_base[['team_code', 'date'] + new_rolling_cols].rename(
    columns={col: f'opp_{col}' for col in new_rolling_cols}
)
matches_with_opponent = matches_rolling_base.merge(
    opponent_rolling_stats,
    left_on=['opp_code', 'date'],
    right_on=['team_code', 'date'],
    suffixes=('', '_opponent_stats'),
    how='left'
).drop(columns=['team_code_opponent_stats'], errors='ignore') # Ignore error if column doesn't exist


# Final column selection and cleaning (matches_cleaned equivalent)
final_columns = ['date', 'venue_code', 'opp_code', 'hour', 'day_code', 'team_code', 'target'] + \
                 new_rolling_cols + \
                 [f'opp_{col}' for col in new_rolling_cols]
final_columns = [col for col in final_columns if col in matches_with_opponent.columns]
matches_cleaned = matches_with_opponent[final_columns].copy()

# Drop rows with ANY missing opponent rolling data
opponent_rolling_cols_prefixed = [f'opp_{col}' for col in new_rolling_cols]
matches_cleaned = matches_cleaned.dropna(subset=opponent_rolling_cols_prefixed)
print(f"'matches_cleaned' equivalent created. Shape: {matches_cleaned.shape}")

# --- 3. Filter for Real Madrid ---
real_madrid_code = 21
print(f"\nFiltering for Real Madrid (team_code={real_madrid_code})...")
rm_matches = matches_cleaned[matches_cleaned['team_code'] == real_madrid_code].copy()
if rm_matches.empty:
    raise ValueError(f"No data found for team code {real_madrid_code}.")
print(f"Filtered Real Madrid data. Shape: {rm_matches.shape}")

# --- 4. Define Final Features & Target for Saving ---
# These are the 20 features for the RM-specific model + the target
final_features_for_model = [
    'venue_code', 'opp_code', 'hour', 'day_code',
    'gf_rolling', 'ga_rolling', 'sh_rolling', 'sot_rolling', 'dist_rolling',
    'fk_rolling', 'pk_rolling', 'pkatt_rolling',
    'opp_gf_rolling', 'opp_ga_rolling', 'opp_sh_rolling', 'opp_sot_rolling',
    'opp_dist_rolling', 'opp_fk_rolling', 'opp_pk_rolling', 'opp_pkatt_rolling'
]
final_target_name = 'target'

# Select only necessary columns from rm_matches (features + target + date for split)
columns_to_split = final_features_for_model + [final_target_name, 'date']
# Verify columns exist
columns_to_split = [col for col in columns_to_split if col in rm_matches.columns]
rm_matches_final_cols = rm_matches[columns_to_split].copy()


# --- 5. Date-based split ---
cutoff_date = "2024-01-01"
print(f"\nSplitting Real Madrid data at date: {cutoff_date}")
train_df_rm = rm_matches_final_cols[rm_matches_final_cols["date"] < cutoff_date]
test_df_rm = rm_matches_final_cols[rm_matches_final_cols["date"] >= cutoff_date]

# Select only feature and target columns for the final CSVs (date no longer needed)
cols_to_save = final_features_for_model + [final_target_name]
train_df_to_save = train_df_rm[cols_to_save]
test_df_to_save = test_df_rm[cols_to_save]

print(f"Final train data shape for saving: {train_df_to_save.shape}")
print(f"Final test data shape for saving: {test_df_to_save.shape}")


# --- 6. Save split files locally ---
os.makedirs("data/split", exist_ok=True)
train_path_local = "data/split/train.csv"
test_path_local = "data/split/test.csv"

print(f"\nSaving processed train data to {train_path_local}")
train_df_to_save.to_csv(train_path_local, index=False)
print(f"Saving processed test data to {test_path_local}")
test_df_to_save.to_csv(test_path_local, index=False)


# --- 7. Upload to S3 ---
prefix = "performance/input" # Or your desired S3 prefix
session = sagemaker.Session()

print(f"\nUploading data to S3 bucket '{bucket}' with prefix '{prefix}'...")
train_s3_uri = session.upload_data(train_path_local, bucket=bucket, key_prefix=f"{prefix}/train")
test_s3_uri = session.upload_data(test_path_local, bucket=bucket, key_prefix=f"{prefix}/test")

print("\nUpload complete:")
print("Train CSV S3 URI:", train_s3_uri)
print("Test CSV S3 URI:", test_s3_uri)
print("\nData preparation and splitting script finished.")