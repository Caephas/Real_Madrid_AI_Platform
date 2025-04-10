# Personalized Content Service Infrastructure (`infra/personalized_content`)

This directory contains the Terraform configuration (.tf files) for provisioning the AWS infrastructure required for the **Personalized Content** service of the Real Madrid AI project.

## Architecture Overview

This Terraform setup provisions the following core AWS resources:

1. **AWS Lambda Function (`personalized-content-service`):**
    * Executes the logic for generating or retrieving personalized content recommendations.
    * Deployed using a Docker image specified by `var.personalized_content_image_uri`.
    * Runs on ARM64 architecture with a 15-second timeout and 512MB memory.
    * Configured with environment variables referencing the DynamoDB table names (`DYNAMODB_ARTICLE_TABLE`, `DYNAMODB_USER_TABLE`).
    * Includes AWS X-Ray active tracing.
    * Uses `data "archive_file"` on the service source code (`../../services/personalized_content`) to generate a `source_code_hash`, ensuring Lambda updates can be triggered by code changes (assuming a corresponding image is built and pushed).
2. **Amazon API Gateway V2 (HTTP API) (`personalized-content-api`):**
    * Exposes the service via public HTTP endpoints.
    * Includes routes:
        * `GET /`: Root path, likely for health checks.
        * `GET /recommendations/{user_id}`: Endpoint to fetch personalized recommendations for a specific user.
    * Integrates with the Lambda function using `AWS_PROXY`.
    * Deploys automatically via a `$default` stage.
3. **Amazon DynamoDB Tables:**
    * **`articles`:** A NoSQL table to store article data, using `article_id` (String) as the primary key.
    * **`users`:** A NoSQL table to store user data or preferences, using `user_id` (String) as the primary key.
    * Both tables are configured with `PAY_PER_REQUEST` billing mode.
4. **AWS ECR Repository (`personalized-content-lambda-repo`):**
    * Private container registry for the Lambda function's Docker image.
    * Set to `force_delete = true`.
5. **IAM Role (`personalized-content-lambda-exec-role`):**
    * Lambda execution role granting necessary permissions:
        * Basic Lambda execution (`AWSLambdaBasicExecutionRole`).
        * CloudWatch logging (`personalized-content-logging-policy`).
        * AWS X-Ray tracing (`AWSXRayDaemonWriteAccess`).
        * DynamoDB access (`personalized-content-dynamodb-access`): Allows `PutItem`, `GetItem`, `Query`, and `Scan` actions on both the `articles` and `users` tables.
6. **CloudWatch Monitoring (via `monitoring.tf`):**
    * **Log Group (`/aws/lambda/personalized-content-service`):** For Lambda function logs (7-day retention).
    * **Dashboard (`personalized-content-service-dashboard`):** Monitors Lambda Invocations, Errors, and P90 Duration.
    * **Alarms:** Triggers alerts for high error counts (`-HighErrors`) or high P90 latency (`-HighLatency`).

## Prerequisites

* **Terraform CLI:** Installed (`terraform version`).
* **AWS Account & Credentials:** Configured AWS credentials with permissions to create the defined resources (Lambda, API Gateway, DynamoDB, ECR, IAM, CloudWatch).
* **Docker Image:** The Docker image for the personalized content service (from `services/personalized_content`) must be built and pushed to the ECR repository URI provided via the `personalized_content_image_uri` variable **before** applying this configuration.

## Configuration

This configuration requires the following input variable, defined in `variables.tf`:

* `personalized_content_image_uri`: (Required) The full URI (including tag) of the pre-built Docker image residing in AWS ECR.

The value for this variable must be provided, typically through a `terraform.tfvars` file (not included in the listing) or other standard Terraform methods (like environment variables `TF_VAR_personalized_content_image_uri=...`).
