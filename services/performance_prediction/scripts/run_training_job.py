from dotenv import load_dotenv
import sagemaker
from sagemaker.sklearn.estimator import SKLearn
from sagemaker.inputs import TrainingInput
from sagemaker.sklearn.model import SKLearnModel
import os

# ENVIRONMENT
load_dotenv(dotenv_path=".env")

role = os.getenv("SAGEMAKER_ROLE_ARN")
bucket = os.getenv("S3_BUCKET")
region = "eu-west-1"

# Initialize SageMaker session
session = sagemaker.Session()
sagemaker_client = session.sagemaker_client

# Define your estimator for training
estimator = SKLearn(
    entry_point="train_entry.py",
    source_dir="training",
    role=role,
    instance_type="ml.m5.large",
    framework_version="1.2-1",
    py_version="py3",
    output_path=f"s3://{bucket}/performance/model",
    base_job_name="real-madrid-performance-model",
)

# Start training job using S3-based date-split train/test input
estimator.fit({
    "train": f"s3://{bucket}/performance/input/train",
    "test": f"s3://{bucket}/performance/input/test"
})

# Create and deploy model
inference_model = SKLearnModel(
    model_data=estimator.model_data,
    role=role,
    entry_point="inference.py",
    source_dir="training",
    framework_version="1.2-1",
    py_version="py3"
)

predictor = inference_model.deploy(
    initial_instance_count=1,
    instance_type="ml.m5.large",
)

print("Model deployed successfully. Endpoint name:", predictor.endpoint_name)