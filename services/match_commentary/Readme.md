# Match Commentary Service (`services/match_commentary`)

This directory contains the Python source code for the Match Commentary service, part of the Real Madrid AI project. It's built using FastAPI and designed for serverless deployment on AWS Lambda.

## Purpose

The service provides an API endpoint to:

1. Fetch live match events for a specified team ID from an external source (API-Football).
2. Store the retrieved events in an AWS DynamoDB table (`match_events`).
3. Generate simple text commentary based on these events.
4. Return the generated commentary to the client.

## API Endpoints

The service exposes the following endpoints (defined in `api/match_commentary_api.py`):

* **`GET /`**
  * Description: Root endpoint, useful for health checks.
  * Response: `{"message": "Match Commentary API is running!"}`

* **`GET /commentary/{team_id}`**
  * Description: Fetches live events for the given `team_id`, stores them in DynamoDB, generates commentary, and returns it.
  * Path Parameter:
    * `team_id` (integer): The ID of the team to fetch commentary for.
  * Success Response (Example):
        ```json
        {
          "team_id": 123,
          "commentary": [
            "An event occurred at 15'!",
            "GOAL! Some Player scores a brilliant goal at 25'!",
            "A yellow card is shown to Another Player at 30'!"
          ]
        }
        ```
  * Response if no live match found:
        ```json
        {"message": "No live matches found for this team."}
        ```

## Core Logic

1. Receives a request at `/commentary/{team_id}`.
2. Uses `utils.api_football.fetch_live_match_events` to call the external API-Football service and retrieve events for the specified team's current live match (if any).
3. If events are found, uses `dynamodb.store_events_in_dynamodb` to save key details of each event to the `match_events` DynamoDB table.
4. Uses `utils.commentary.generate_commentary` to create a simple commentary string for each event based on its type.
5. Returns the list of commentary strings.

## Dependencies

* **External Services:**
  * API-Football (or similar configured via environment variables) for live match data.
* **AWS Services (Provisioned by Terraform in `infra/match_commentary`):**
  * AWS Lambda (for execution)
  * Amazon API Gateway V2 (HTTP API) (for exposure)
  * Amazon DynamoDB (for storing events)
  * Amazon ECR (for hosting the Docker image)
  * Amazon CloudWatch (for logging and monitoring)
  * AWS IAM (for permissions)
* **Python Libraries:**
  * FastAPI: Web framework.
  * Mangum: ASGI adapter for AWS Lambda + API Gateway.
  * Requests: For making HTTP calls to the external API.
  * Boto3: AWS SDK for Python (used for DynamoDB interaction).
  * python-dotenv: For loading environment variables from a `.env` file during local development.
  * *(See project's `pyproject.toml` or `requirements.txt` for a full list)*

## Environment Variables

The service requires the following environment variables:

* `API_FOOTBALL_BASE_URL`: The base URL for the external football API.
* `API_FOOTBALL_KEY`: The API key for the external football API.
* `DYNAMODB_TABLE`: The name of the DynamoDB table to store match events (defaults to `match_events` if not set, but explicitly set by Terraform).

These are loaded via `utils/env.py` using `python-dotenv` for local development (expects a `.env` file in the project root or parent directory). For AWS deployment, these are configured in the Lambda function's environment settings via Terraform (`infra/match_commentary/main.tf`).

## Local Development & Setup

1. **Environment:** Ensure you have Python and Poetry (or your project's package manager) installed.
2. **Dependencies:** Navigate to the project root directory and install dependencies (e.g., `poetry install`).
3. **Configuration:** Create a `.env` file in the project root (or where `utils/env.py` expects it) and add the required environment variables:

    ```dotenv
    API_FOOTBALL_BASE_URL=[https://your-api-url.com/](https://your-api-url.com/)
    API_FOOTBALL_KEY=your_api_football_secret_key
    DYNAMODB_TABLE=match_events # Or your local table name if using DynamoDB Local
    ```

4. **Run Locally:** Use an ASGI server like Uvicorn. From the `services/match_commentary` directory, run:

    ```bash
    uvicorn main:app --reload --port 8001 # Or another suitable port
    ```

    You can then access the API at `http://localhost:8001`.

## Deployment

* **Infrastructure:** The AWS infrastructure (Lambda, API Gateway, DynamoDB, ECR Repo, IAM Roles, Monitoring) is managed by Terraform in the `infra/match_commentary` directory.
* **Orchestration:** The `Makefile` in this directory (`services/match_commentary`) helps orchestrate the deployment process:
  * `make build`: Builds the Docker image for the service.
  * `make tag`: Tags the image correctly for the ECR repository.
  * `make login`: Logs Docker into the AWS ECR registry.
  * `make push`: Pushes the tagged image to ECR.
  * `make deploy-ecr`: (Uses Terraform) Creates the ECR repository if it doesn't exist.
  * `make deploy-all`: (Uses Terraform) Deploys all other infrastructure defined in `infra/match_commentary`.
  * `make monitoring`, `make alerts`: (Uses Terraform) Applies monitoring resources.
  * `make all`: Runs the common sequence: build, tag, deploy ECR, push image, deploy infrastructure, apply monitoring/alerts.
  * `make destroy`: (Uses Terraform) Destroys the infrastructure defined in `infra/match_commentary`.
* Refer to the README in `infra/match_commentary` for details on Terraform prerequisites and configuration.

## Folder Structure

* `api/`: Contains FastAPI route definitions (`match_commentary_api.py`).
* `utils/`: Contains helper modules:
  * `api_football.py`: Logic for interacting with the external football API.
  * `commentary.py`: Logic for generating commentary strings.
  * `env.py`: Handles loading environment variables.
* `dynamodb.py`: Logic for interacting with the DynamoDB table.
* `main.py`: Main application entry point using FastAPI and Mangum adapter for Lambda.
* `Makefile`: Defines commands for building, pushing, deploying, and destroying the service and its infrastructure.