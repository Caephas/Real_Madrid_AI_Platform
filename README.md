# **Real Madrid AI Backend**

A **microservice-based backend** designed to enhance Real Madrid fan engagement through AI-powered insights, personalized content, real-time match commentary, and predictive analytics. This backend leverages cutting-edge machine learning models, fine-tuned Large Language Models (LLMs), and scalable cloud technologies to deliver an interactive and immersive experience for fans.

---

## **Table of Contents**
1. [Features](#features)
2. [Technologies Used](#technologies-used)
3. [Architecture](#architecture)
4. [Setup Instructions](#setup-instructions)
5. [Environment Variables](#environment-variables)
6. [Endpoints and API Documentation](#endpoints-and-api-documentation)
7. [Data Sources](#data-sources)
8. [Project Structure](#project-structure)

---

## **Features**

### 1. **Chatbot**
- **Description**: NLP-driven chatbot powered by a fine-tuned Large Language Model (LLM) to answer Real Madrid-related queries.
- **Example Queries**:
  - "Who is Real Madrid's captain?"
  - "How many trophies has Real Madrid won?"
- **Technology**: Hugging Face Transformers, fine-tuned Llama model.

### 2. **Real-Time Match Commentary**
- **Description**: Provides live match updates and commentary using real-time data from API-Football.
- **Key Features**:
  - Fetches live match events (e.g., goals, fouls, substitutions).
  - Generates detailed commentary for fan engagement.

### 3. **Performance Prediction**
- **Description**: Predicts match outcomes using historical match data and machine learning models.
- **Key Features**:
  - Leverages advanced ML models (e.g., Random Forest, XGBoost) for predictions.
  - Provides probabilities for Win, Draw, or Loss.

### 4. **Personalized Content Recommendations**
- **Description**: Recommends articles and news tailored to fan preferences.
- **Key Features**:
  - Scrapes news articles from RSS feeds.
  - Stores and retrieves articles using Firestore.
  - Recommends articles based on user preferences and interactions.

---

## **Technologies Used**

### **Programming Languages**
- Python

### **Frameworks and Libraries**
- **Backend**: FastAPI
- **NLP and ML**: Hugging Face Transformers, scikit-learn, XGBoost, LightGBM
- **Database**: Firebase Firestore
- **Data Processing**: Pandas, NumPy
- **Web Scraping**: Feedparser

### **APIs**
- **API-Football**: Fetch live match data and statistics.

### **Other Tools**
- Docker: Containerization for deployment.
- Poetry: Dependency management and environment setup.

---

## **Architecture**

The project is designed as a modular microservice-based system:

1. **Microservices**:
   - Each feature (chatbot, match commentary, prediction, content) is implemented as an independent service.
2. **Shared Components**:
   - Utilities like Firestore database operations are centralized in a shared folder.
3. **Scalability**:
   - Dockerized for easy deployment and scalability.
4. **Data Flow**:
   - External APIs and datasets feed the backend for predictions, content generation, and real-time commentary.

---

## **Setup Instructions**

### **1. Clone the Repository**
```bash
git clone https://github.com/Caephas/Real_Madrid_AI_Platform
cd eal_Madrid_AI_Platform

2. Set Up a Virtual Environment

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install Dependencies

Using Poetry:

poetry install

4. Set Up Environment Variables
	•	Create a .env file in the root directory.
	•	Add the following environment variables:

API_FOOTBALL_BASE_URL=<your-api-football-base-url>
API_FOOTBALL_KEY=<your-api-football-key>


	• Note: Firebase and Google Cloud credentials are handled via Application Default Credentials (ADC). You can learn more about setting up ADC here.

5. Run the Application

poetry run uvicorn backend.<service-name>:app --reload

Replace <service-name> with the specific microservice you want to test (e.g., chatbot.api.chatbot_api).

Environment Variables

Variable	Description
API_FOOTBALL_BASE_URL	The base URL for API-Football.
API_FOOTBALL_KEY	API key for accessing API-Football.

	Note: Google Cloud and Firebase services rely on Application Default Credentials (ADC). Ensure ADC is set up on your local environment or deployment platform.

Setting Up ADC
	1. Authenticate using gcloud:

gcloud auth application-default login


	2. Ensure the correct project is active:

gcloud config set project <your-project-id>


	3. Verify ADC setup:

gcloud auth application-default print-access-token

For detailed guidance, refer to the official documentation.

Endpoints and API Documentation

Microservice	Endpoint	Description
Chatbot	/chat	Handles user queries and returns AI-generated responses.
Match Commentary	/live_match_data	Fetches and stores live match events for commentary.
Performance Prediction	/predict_match	Predicts match outcomes based on pre-match data.
Personalized Content	/recommend_articles	Provides personalized news recommendations based on user preferences.

Data Sources
1. Historical Match Data:
 • cleaned_laliga_matches.csv: Preprocessed match data for model training and predictions.
 • la_liga_10_seasons.csv: Raw match data for La Liga.
2. News Articles:
 • Scraped from RSS feeds (e.g., Managing Madrid).
3. LLM Fine-Tuning Data:
 • real_madrid_facts.jsonl: Domain-specific data for fine-tuning the chatbot.

Project Structure

Real-Madrid-AI-project/
│
├── backend/
│   ├── chatbot/                  # Chatbot microservice
│   ├── match_commentary/         # Real-time match commentary microservice
│   ├── performance_prediction/   # Match outcome prediction microservice
│   ├── personalized_content/     # Content recommendation microservice
│   ├── shared/                   # Shared utilities (e.g., Firestore operations)
│
├── data/                         # Datasets and processed data
│   ├── cleaned_laliga_matches.csv
│   ├── la_liga_10_seasons.csv
│   ├── real_madrid_10_seasons.csv
│   ├── real_madrid_facts.jsonl
│
├── notebooks/                    # Jupyter notebooks for data preprocessing and analysis
│   ├── real-madrid-EDA.ipynb
│   ├── scrape_data.ipynb
│
├── .env                          # Environment variables
├── .gitignore                    # Git ignore file
├── Dockerfile                    # Dockerfile for containerization
├── pyproject.toml                # Poetry project configuration
