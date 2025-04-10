# Match Commentary Service Infrastructure (`infra/match_commentary`)

This directory contains the Terraform configuration (.tf files) used to provision and manage the AWS infrastructure for the **Match Commentary** service within the Real Madrid AI project.

## Architecture Overview

This Terraform configuration deploys the following AWS resources:

1. **AWS Lambda Function (`match-commentary-service`):**
    * Contains the logic for generating or retrieving match commentary.
    * Deployed using a Docker image specified by `var.match_commentary_image_uri`.
    * Uses ARM64 architecture.
    * Configured with a 15-second timeout and 512MB memory.
    * Requires environment variables: `API_FOOTBALL_BASE_URL`, `API_FOOTBALL_KEY`, `DYNAMODB_TABLE="match_events"`.
    * Has AWS X-Ray tracing enabled (`Active`).
    * Uses `data "archive_file"` on the service source code primarily to generate a `source_code_hash`, ensuring Lambda updates are triggered when the underlying service code changes (even if the image tag in the variable remains the same, implying a new image *should* be built and pushed).
2. **Amazon API Gateway V2 (HTTP API) (`match-commentary-api`):**
    * Provides public HTTP endpoints to access the commentary service.
    * Configured with routes:
        * `GET /`: Root route (likely for health checks or basic info).
        * `GET /commentary/{team_id}`: Endpoint to retrieve commentary for a specific team.
    * Uses `AWS_PROXY` integration with the Lambda function.
    * Includes a `$default` stage with auto-deployment enabled.
3. **Amazon DynamoDB Table (`match_events`):**
    * A NoSQL database table likely used to store match events or commentary snippets.
    * Uses `event_id` (String) as the primary hash key.
    * Configured with `PAY_PER_REQUEST` billing mode.
4. **AWS ECR Repository (`match-commentary-lambda-repo`):**
    * A private container registry to store the Docker image for the Lambda function.
    * Set to `force_delete = true` (allows deletion even if images exist - use carefully).
5. **IAM Role (`match-commentary-lambda-exec-role`):**
    * Execution role for the Lambda function.
    * Grants permissions for:
        * Basic Lambda execution (`AWSLambdaBasicExecutionRole`).
        * Writing logs to CloudWatch (`match-commentary-logging-policy`).
        * Sending trace data to AWS X-Ray (`AWSXRayDaemonWriteAccess`).
        * Writing items to the `match_events` DynamoDB table (`match-commentary-dynamodb-write` policy allowing `PutItem`).
6. **CloudWatch Resources:**
    * **Log Group (`/aws/lambda/match-commentary-service`):** Stores Lambda logs (7-day retention).
    * **Dashboard (`match-commentary-service-dashboard`):** Monitors Lambda Invocations, Errors, and P90 Duration.
    * **Alarms:**
        * `match-commentary-service-HighErrors`: Triggers on any errors in 1 minute.
        * `match-commentary-service-HighLatency`: Triggers if P90 duration exceeds 1 second in 1 minute.

## Prerequisites

* **Terraform CLI:** Installed and configured (`terraform version`).
* **AWS Account & Credentials:** Configured AWS credentials with sufficient permissions to create the resources defined.
* **Docker Image:** The Docker image for the match commentary service must be built (based on code in `services/match_commentary`) and pushed to the ECR repository URI provided in the `match_commentary_image_uri` variable **before** applying this configuration.

## Configuration

Input variables are defined in `variables.tf`:

* `match_commentary_image_uri`: (Required) The full URI (including tag) of the pre-built Docker image in ECR.
* `api_football_key`: (Required) The API key for accessing the API-Football service.
* `api_football_base_url`: (Required) The base URL for the API-Football service.

Values for these variables need to be provided, typically via a `terraform.tfvars` file (which was not included in the listing) or environment variables.

**Security Note:** Be cautious about storing the `api_football_key` directly in version control (e.g., in a `.tfvars` file). Consider using more secure methods like environment variables (`export TF_VAR_api_football_key="..."`), AWS Secrets Manager, or Systems Manager Parameter Store.
