import pandas as pd
import os
import sagemaker
from dotenv import load_dotenv

load_dotenv(dotenv_path="services/performance_prediction/.env")
# Load data
df = pd.read_csv("data/cleaned_laliga_matches.csv")
df["date"] = pd.to_datetime(df["date"])

# Date-based split
cutoff_date = "2023-06-04"
train_df = df[df["date"] < cutoff_date]
test_df = df[df["date"] > cutoff_date]

# Save split files locally
os.makedirs("data/split", exist_ok=True)
train_path_local = "data/split/train.csv"
test_path_local = "data/split/test.csv"

train_df.to_csv(train_path_local, index=False)
test_df.to_csv(test_path_local, index=False)

# Upload to S3
bucket = os.environ["S3_BUCKET"]
prefix = "performance/input"
session = sagemaker.Session()

train_s3_uri = session.upload_data(train_path_local, bucket=bucket, key_prefix=f"{prefix}/train")
test_s3_uri = session.upload_data(test_path_local, bucket=bucket, key_prefix=f"{prefix}/test")

print("✅ Uploaded to S3:")
print("Train CSV:", train_s3_uri)
print("Test CSV:", test_s3_uri)