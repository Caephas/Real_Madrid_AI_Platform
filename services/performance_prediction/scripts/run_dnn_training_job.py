import os
from dotenv import load_dotenv
import sagemaker
from sagemaker.pytorch import PyTorch

load_dotenv(dotenv_path=".env")

role = os.getenv("SAGEMAKER_ROLE_ARN")
bucket = os.getenv("S3_BUCKET")

session = sagemaker.Session()

estimator = PyTorch(
    entry_point="train_dnn.py",
    source_dir="training",
    role=role,
    instance_type="ml.m5.large",
    instance_count=1,
    framework_version="2.1.0",
    py_version="py310",
    output_path=f"s3://{bucket}/performance/dnn-model",
    hyperparameters={"epochs": 10},
    base_job_name="real-madrid-dnn"
)

estimator.fit({
    "train": f"s3://{bucket}/performance/input/train",
    "test": f"s3://{bucket}/performance/input/test"
})