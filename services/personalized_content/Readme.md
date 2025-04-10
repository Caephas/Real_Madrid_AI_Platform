# Personalized Content Service (`services/personalized_content`)

This directory contains the Python source code for the Personalized Content service. It includes a FastAPI application (deployed via AWS Lambda) to serve recommendations and a utility script to fetch, categorize, and store articles.

## Purpose

The primary goal of this service is to provide personalized article recommendations to users based on their preferences. It involves:

1. **Article Ingestion:** Periodically fetching articles from an external RSS feed (`managingmadrid.com`), categorizing them using basic NLP (spaCy), and storing them in the `articles` DynamoDB table (`utils/fetch_and_store_articles.py`).
2. **Recommendation API:** An API endpoint that retrieves a user's preferences from the `users` DynamoDB table, fetches relevant articles from the `articles` table based on those preferred categories, and returns a sorted list of recommended articles (`api/recommendations_api.py`).

## Components

* **Recommendation API (`main.py`, `api/`):** A FastAPI application adapted for AWS Lambda using Mangum. Handles user requests for recommendations.
* **Article Fetcher (`utils/fetch_and_store_articles.py`):** A script intended to be run separately (e.g., scheduled task, manually) to populate the `articles` DynamoDB table from an RSS feed. Uses spaCy for categorization.
* **DynamoDB Interaction (`dynamodb.py`):** Contains functions for interacting with both the `users` and `articles` DynamoDB tables.
* **Deployment Tools (`Dockerfile`, `Makefile`):** Used to build the service container image and orchestrate deployment using Docker and Terraform.

## API Endpoints

Defined in `api/recommendations_api.py`:

* **`GET /`**
  * Description: Root endpoint for health checks.
  * Response: `{"message": "Personalized Content API is running!"}`

* **`GET /recommendations/{user_id}`**
  * Description: Fetches article recommendations for a specific user.
  * Path Parameter:
    * `user_id` (string): The ID of the user requesting recommendations.
  * Success Response (Example):

        ```json
        {
          "user_id": "user123",
          "recommendations": [
            {
              "article_id": "...", "title": "...", "link": "...", "published": "...", "category": "Match Previews", ...
            },
            {
              "article_id": "...", "title": "...", "link": "...", "published": "...", "category": "Transfers", ...
            }
          ]
        }
        ```

  * Error Response (User not found/no preferences):

        ```json
        {"error": "User not found or has no preferences"}
        ```

## Dependencies

* **External Services:**
  * RSS Feed Source (`www.managingmadrid.com/rss/current.xml`).
* **Python Libraries:**
  * FastAPI, Mangum, Boto3, Requests, python-dotenv, feedparser, spaCy (`en_core_web_sm` model), Poetry (for dependency management).
* **AWS Services (Provisioned by Terraform in `infra/personalized_content`):**
  * AWS Lambda, Amazon API Gateway V2 (HTTP API), Amazon DynamoDB (x2 tables), Amazon ECR, Amazon CloudWatch, AWS IAM.

## Critical Infrastructure Note TODO: DynamoDB GSI

* The `get_articles_by_category` function in `dynamodb.py` requires a **Global Secondary Index (GSI)** named `category-index` on the `articles` DynamoDB table.
* This index must use `category` (String) as its hash key to allow efficient querying by category.

## Environment Variables

The **API Lambda function** requires:

* `DYNAMODB_ARTICLE_TABLE`: Name of the articles DynamoDB table (e.g., "articles").
* `DYNAMODB_USER_TABLE`: Name of the users DynamoDB table (e.g., "users").

The **`Workspace_and_store_articles.py` script** requires:

* `DYNAMODB_ARTICLE_TABLE`: Name of the articles DynamoDB table.
* AWS Credentials (implicitly via Boto3's standard credential chain) to write to DynamoDB.
* Access to the `spacy` `en_core_web_sm` model.

For local development, these can be set in a `.env` file (loaded by `utils/env.py` where applicable, though `Workspace_and_store_articles.py` uses `os.environ.get`). For deployment, they are set in the Lambda environment via Terraform.

## Setup & Local Development

1. **Environment:** Python and Poetry installed.
2. **Dependencies:** Run `poetry install` from the project root.
3. **SpaCy Model:** Download the required model: `python -m spacy download en_core_web_sm`
4. **Configuration:** Create a `.env` file in the project root (or appropriate location) with `DYNAMODB_ARTICLE_TABLE` and `DYNAMODB_USER_TABLE` (if running locally against AWS or DynamoDB Local). Configure AWS credentials if running scripts locally.
5. **Run API Locally:** From `services/personalized_content`, use `uvicorn main:app --reload --port 8002` (or another port).
6. **Run Fetcher Script:** From the project root or configured environment, run `python services/personalized_content/utils/fetch_and_store_articles.py`.

## Deployment

* **Infrastructure:** Managed via Terraform in `infra/personalized_content`. **Remember to add the DynamoDB GSI mentioned above.**
* **Orchestration:** The `Makefile` provides commands:
  * `make build`: Builds the Docker image using the `Dockerfile`.
  * `make push`: Pushes the image to the ECR repository (requires `make login` first).
  * `make all`: Complete build, push, and Terraform deployment sequence.
  * `make deploy-ecr`, `make deploy-all`: Terraform deployment steps.
  * `make destroy`: Destroys Terraform resources and attempts ECR cleanup.
* Ensure the `en_core_web_sm` spaCy model is included in the Docker image if `Workspace_and_store_articles.py` is intended to run within the same container environment or if the main API needs it (currently doesn't seem to). If the fetcher script runs elsewhere, ensure that environment has spaCy and the model.

## Folder Structure

* `api/`: Contains FastAPI route definitions (`recommendations_api.py`).
* `utils/`: Contains helper modules:
  * `Workspace_and_store_articles.py`: Script for RSS fetching, categorization, and storage.
  * *(Likely missing `env.py` if used by API, check imports)*
* `dynamodb.py`: Functions for DynamoDB interactions.
* `main.py`: FastAPI application entry point with Mangum adapter.
* `Dockerfile`: Instructions for building the service container image.
* `Makefile`: Orchestration commands for build, deployment, cleanup.
