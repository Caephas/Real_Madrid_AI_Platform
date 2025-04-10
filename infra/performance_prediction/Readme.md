# Performance Prediction Infrastructure (`infra/performance_prediction`)

This directory contains Terraform configuration (.tf files) for provisioning foundational AWS infrastructure components required by the **Performance Prediction** service, primarily focusing on data storage and IAM permissions for AWS SageMaker.

## Resources Created

This Terraform setup deploys the following AWS resources:

1. **S3 Bucket (`real-madrid-performance-data-bucket`):**
    * An S3 bucket intended to store datasets (e.g., `train.csv`, `test.csv`), trained model artifacts (`.joblib`/`.pkl` files within `model.tar.gz`), and potentially other data related to the performance prediction machine learning lifecycle.
    * Configured with `force_destroy = true`, allowing the bucket to be deleted by Terraform even if it contains objects (use with caution, especially with valuable data or models).
2. **IAM Role (`sagemaker-performance-execution-role`):**
    * An execution role designed to be assumed by AWS SageMaker services (like Training Jobs, Endpoints, Notebook Instances) when performing tasks related to performance prediction.
3. **IAM Policy Attachments:**
    * Attaches broad AWS managed policies to the SageMaker execution role:
        * `arn:aws:iam::aws:policy/AmazonSageMakerFullAccess`
        * `arn:aws:iam::aws:policy/AmazonS3FullAccess`

    **Security Note:** Attaching `AmazonSageMakerFullAccess` and especially `AmazonS3FullAccess` grants very broad permissions. For production or security-sensitive environments, it is strongly recommended to **scope these policies down** following the principle of least privilege. For example, limit S3 access strictly to the necessary buckets (like `real-madrid-performance-data-bucket`) and specific actions (`s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, etc.) required by your SageMaker workflows.

## Prerequisites

* **Terraform CLI:** Ensure Terraform is installed (`terraform version`).
* **AWS Account & Credentials:** Configured AWS credentials with permissions to create S3 buckets and IAM roles/policies.

## Configuration

Input variables are defined in `variables.tf`:

* `bucket_name`: The name for the S3 bucket. Defaults to `real-madrid-performance-data-bucket`.

Values can be provided via a `terraform.tfvars` file (not included in the listing) or other standard Terraform variable input methods if you need to override the default bucket name.

## Outputs

After a successful `apply`, Terraform will output the following values (defined in `outputs.tf`):

* `sagemaker_role_arn`: The ARN of the created SageMaker execution role. This ARN is typically required when configuring SageMaker Training Jobs, Endpoints, Notebook Instances, etc.
* `performance_bucket_name`: The name of the created S3 bucket.

## Monitoring (Important Note)

The included `monitoring.tf` file defines CloudWatch resources (Dashboard, Alarms) that target metrics within the `AWS/Lambda` namespace using a `FunctionName` dimension. **However, the `main.tf` in this directory does not create any Lambda function.**

Therefore, the resources defined in `monitoring.tf` **will likely not function correctly or monitor relevant metrics** for the S3 bucket or IAM role created here. Monitoring for SageMaker activities (Training Jobs, Endpoints) is typically done via the SageMaker console, specific SageMaker CloudWatch metrics (e.g., in the `AWS/SageMaker` namespace), or SageMaker's built-in monitoring features. **This `monitoring.tf` file should likely be removed or significantly revised** if specific monitoring for *this* infrastructure (e.g., S3 bucket metrics) is desired.
