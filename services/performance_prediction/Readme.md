# Performance Prediction Service (`services/performance_prediction`)

This directory contains the scripts and code supporting the MLOps lifecycle for the Real Madrid match outcome prediction model. It includes components for data preparation, model training on AWS SageMaker, inference handling, and example endpoint invocation.

## Workflow Overview

The primary workflow, often orchestrated by the `Makefile`, involves these steps:

1. **Data Preparation (`scripts/split_data.py`):**
    * Loads raw match data (`data/combined_la_liga.csv`).
    * Performs extensive preprocessing (encoding, rolling averages, opponent stat merging).
    * Filters data specifically for Real Madrid matches.
    * Selects the final 20 features and the target variable.
    * Splits the processed Real Madrid data chronologically into `train.csv` and `test.csv`.
    * Uploads these CSV files to a specified S3 bucket (`performance/input/`).
2. **Model Training (`scripts/run_training_job.py` & `training/train_entry.py`):**
    * `run_training_job.py` uses the SageMaker Python SDK to launch a training job.
    * The job executes `training/train_entry.py` on a SageMaker instance.
    * `train_entry.py` loads the `train.csv` and `test.csv` from S3.
    * Applies SMOTE to the training data to handle class imbalance.
    * Trains a `RandomForestClassifier` model using the defined 20 features on the SMOTE-resampled data.
    * Saves the trained model artifact (`randomforest_model.pkl`) to S3 via `/opt/ml/model`.
    * Evaluates the model on the test set and prints metrics.
3. **Model Deployment (`scripts/run_training_job.py`):**
    * After successful training, `run_training_job.py` uses the trained model artifact (`model_data`) and the inference script (`training/inference.py` / `training/sagemaker_serving.py`) to create an `SKLearnModel`.
    * Deploys this model to a real-time SageMaker endpoint.
4. **Inference Handling (`training/sagemaker_serving.py`):**
    * Defines the functions (`model_fn`, `input_fn`, `predict_fn`, `output_fn`) required by SageMaker for hosting the scikit-learn model.
    * Loads the saved `randomforest_model.pkl`.
    * Handles incoming JSON requests, converts them to Pandas DataFrames.
    * Uses the model's `predict_proba` method to get probabilities for Loss, Draw, and Win.
    * Formats the output as a JSON response containing class probabilities.
5. **Example Invocation (`api/match_prediction_api.py`):**
    * Provides a sample standalone script demonstrating how to use `boto3` to invoke the deployed SageMaker endpoint with sample (placeholder) input data. **Note:** This is a client example, not a deployed API within this service directory.

## Components

* **`api/`:** Contains example client code (`match_prediction_api.py`) for invoking the deployed endpoint.
* **`scripts/`:** Contains scripts to orchestrate the MLOps workflow:
  * `split_data.py`: Data preprocessing, filtering, splitting, and S3 upload.
  * `run_training_job.py`: Launches SageMaker training and deployment using the SageMaker SDK.
* **`training/`:** Contains code executed *within* the SageMaker training/inference environments:
  * `train_entry.py`: The main script for the SageMaker training job (data loading, SMOTE, training, evaluation, model saving).
  * `sagemaker_serving.py`: Defines the inference handler functions (`model_fn`, `input_fn`, etc.).
  * `inference.py`: (Likely imports and uses functions from `sagemaker_serving.py`, referenced by `SKLearnModel` in `run_training_job.py`).
* **`Makefile`:** Defines `make` commands to simplify running the workflow steps (data split, training/deployment, prediction test, cleanup).

## Prerequisites

* **Python Environment:** With libraries installed run `poetry install` from root. Key libraries: `pandas`, `numpy`, `scikit-learn`, `imbalanced-learn`, `boto3`, `sagemaker`, `python-dotenv`, `joblib`.
* **AWS Credentials:** Configured AWS credentials with permissions for S3 access, SageMaker (training, deployment, roles), and IAM role creation (if running infra setup).
* **SageMaker Execution Role ARN:** An existing IAM Role ARN that SageMaker can assume (created by `infra/performance_prediction`).
* **S3 Bucket:** An existing S3 bucket name.
* **`.env` File:** Expected in `services/performance_prediction/` (or project root, check `load_dotenv` path), containing at least:
  * `SAGEMAKER_ROLE_ARN=arn:aws:iam::...:role/...`
  * `S3_BUCKET=your-s3-bucket-name`

## Configuration

* Environment variables (`SAGEMAKER_ROLE_ARN`, `S3_BUCKET`) are loaded from a `.env` file via `python-dotenv` in the scripts.
* The `train_entry.py` script uses hardcoded feature lists and model parameters (can be parameterized using SageMaker hyperparameters if needed).
* The `split_data.py` script uses a hardcoded `cutoff_date` for splitting.

## Usage / Key Makefile Commands

Navigate to the `services/performance_prediction` directory. Ensure your `.env` file is correctly populated.

* **`make setup`**: (Uses Terraform) Provisions the required infrastructure (S3 bucket, IAM role) defined in `infra/performance_prediction`. Run once initially.
* **`make split-data`**: Runs the data preparation script (`scripts/split_data.py`) to process data and upload `train.csv` and `test.csv` to S3.
* **`make train`**: Runs the script (`scripts/run_training_job.py`) to launch the SageMaker training job using the data from S3, and subsequently deploys the trained model to an endpoint.
* **`make predict`**: Runs the example invocation script (`api/match_prediction_api.py`) to send sample data to the deployed endpoint (Note: endpoint name might be hardcoded or need updating in the script).
* **`make all`**: Runs `setup`, `split-data`, and `train` sequentially.
* **`make clean`**: Removes model artifacts and input data from the S3 bucket.
* **`make destroy`**: (Uses Terraform) Destroys the infrastructure defined in `infra/performance_prediction`.
* **`make destroy-all`**: Runs `clean` and `destroy`.

## Notes

* The model trained is specific to Real Madrid match outcomes.
* The inference script (`sagemaker_serving.py`) returns prediction *probabilities* for each class (Loss, Draw, Win).
* The `api/match_prediction_api.py` script requires significant modification (removing placeholders, adding logic to fetch real-time features) to be used for actual predictions on upcoming matches.
