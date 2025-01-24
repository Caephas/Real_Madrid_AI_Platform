# **Real Madrid AI Backend**
![image info](./logo.png)
As a passionate Real Madrid fan, I developed this project as a side project to explore the intersection of football and AI. This **microservice-based backend** enhances Real Madrid fan engagement through AI-powered insights, personalized content, real-time match commentary, and predictive analytics. The platform utilizes machine learning models, fine-tuned Large Language Models (LLMs), and scalable cloud technologies to give fans a more engaging eperience.

## **Features**

### 1. **Chatbot**
- **Description**: A chatbot powered by a fine-tuned Large Language Model (LLM) unsloth/gemma-2b-bnb-4bit [Unsloth](https://github.com/unslothai/unsloth) that answers Real Madrid-related queries.
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
  - Leverages advanced ML models (e.g., Random Forest, XGBoost).
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
- **Web Scraping**: [FBREF](https://fbref.com)  

### **APIs**
- **API-Football**: Fetch live match data and statistics.

### **Other Tools**
- **Docker**: Containerization for deployment.  
- **Poetry**: Dependency management and environment setup.

---

## **Architecture**

The project is designed as a modular, microservice-based system:

1. **Microservices**  
   Each feature (chatbot, match commentary, prediction, content) is implemented as an independent service.
2. **Shared Components**  
   Utilities like Firestore database operations are centralized in a shared folder.
3. **Scalability**  
   Dockerized for easy deployment and scalability.
4. **Data Flow**  
   External APIs and datasets feed the backend for predictions, content generation, and real-time commentary.

---

## **Setup Instructions**

### **1. Clone the Repository**

```bash
git clone https://github.com/Caephas/Real_Madrid_AI_Platform
cd Real_Madrid_AI_Platform

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

FIREBASE_TYPE=<your-firebase-type>
FIREBASE_PROJECT_ID=<your-firebase-project-id>
FIREBASE_PRIVATE_KEY_ID=<your-private-key-id>
FIREBASE_PRIVATE_KEY=<your-private-key>  # Replace "\n" with actual newlines if required
FIREBASE_CLIENT_EMAIL=<your-client-email>
FIREBASE_CLIENT_ID=<your-client-id>
FIREBASE_AUTH_URI=<your-auth-uri>
FIREBASE_TOKEN_URI=<your-token-uri>
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=<your-auth-provider-cert-url>
FIREBASE_CLIENT_X509_CERT_URL=<your-client-cert-url>

	•	Ensure all variables are correctly set in the .env file.

5. Build and Run the Docker Image:
  1. Build the Docker Image:
   docker build -t real-madrid-ai-backend .
  2. docker run -d -p 8000:8000 real-madrid-ai-backend
```


## Project Structure


## **Endpoints and API Documentation**

| **Microservice**          | **Endpoint**              | **Method** | **Description**                                        |
|---------------------------|---------------------------|------------|-------------------------------------------------------|
| **Chatbot**               | `/chatbot`                      | `GET`      | Health check for the Chatbot microservice.            |
|                           | `/chatbot/chat`                  | `POST`     | Handles user queries and returns AI-generated responses. |
| **Match Commentary**      | `/commentary`                      | `GET`      | Health check for the Match Commentary microservice.   |
|                           | `/commentary/{team_id}`       | `GET`      | Fetches and stores live match events for commentary.   |
| **Performance Prediction**| `/prediction`                      | `GET`      | Health check for the Performance Prediction microservice. |
|                           | `/prediction/match`         | `POST`     | Predicts match outcomes based on pre-match data.      |
| **Personalized Content**  | `/recommendations`                      | `GET`      | Health check for the Personalized Content microservice. |
|                           | `/recommendations/{user_id}`    | `GET`      | Provides personalized news recommendations.           |****

## **Data Sources**

1. **Historical Match Data**:
   - `cleaned_laliga_matches.csv`: Preprocessed match data for model training and predictions.
   - `la_liga_10_seasons.csv`: Raw match data for La Liga.

2. **News Articles**:
   - Scraped from RSS feeds (e.g., Managing Madrid).

3. **LLM Fine-Tuning Data**:
   - `real_madrid_facts.jsonl`: Domain-specific data for fine-tuning the chatbot.
```
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

```
## **Improvements**

While the current implementation provides a solid foundation, the following enhancements can improve the overall application and user experience:

### **1. Implement Cron Jobs for Automation**
- **Purpose**: Automate repetitive tasks like fetching live match data or scraping news articles periodically.
- **Proposed Features**:
  - Fetch new match events every 5 minutes using API-Football.
  - Scrape and categorize fresh articles from RSS feeds daily.
- **Tools**: Use a task scheduler like `cron` .

### **2. Enhanced Chatbot with Multi-Turn Conversations**
- **Purpose**: Improve chatbot interaction by enabling contextual, multi-turn conversations.
- **Proposed Features**:
  - Maintain chat history to provide more personalized and contextual responses.
  - Use a better model and gather more data for finetuning

### **3. Add User Authentication and Profiles**
- **Purpose**: Personalize recommendations and predictions for authenticated users.
- **Proposed Features**:
  - Add sign-up and login functionality with Firebase Authentication.
  - Store user preferences, chat history, and saved articles in Firestore.
- **Tools**: Leverage Firebase Authentication and Firestore for seamless integration.

### **4. Scalable Deployment with Kubernetes**
- **Purpose**: Enhance the scalability and reliability of the backend.
- **Proposed Features**:
  - Deploy the microservices in a Kubernetes cluster for load balancing and fault tolerance.
  - Set up horizontal pod autoscaling to handle increased traffic during matches.
- **Tools**: Use Kubernetes with a cloud provider (e.g., GKE, EKS).

### **5. Advanced Machine Learning Models**
- **Purpose**: Improve the accuracy of predictions and recommendations.
- **Proposed Features**:
  - Train deep learning models for performance prediction using PyTorch.
  - Implement collaborative filtering or content-based recommendations for personalized articles.