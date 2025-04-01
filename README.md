# **Real Madrid AI Platform**

![Real Madrid AI](./logo.png)

This project is a **modular AI-powered backend platform** built to enhance Real Madrid fan engagement through intelligent insights, predictions, and personalized content. It features real-time commentary, match outcome prediction, a custom chatbot, and personalized news — all deployed with scalable infrastructure on **AWS using Terraform, SageMaker, Lambda, and ECR**.

Built by a Real Madrid fan, for Real Madrid fans. 🤍⚽

---

## Features

### 1. Chatbot

- **Gemini LLM**
- **Handles natural queries** about players, trophies, match stats, and history.
- **Deployed on AWS Lambda** with FastAPI + Mangum.

### 2. Real-Time Match Commentary

- **Fetches live events** via API-Football.
- **Generates human-readable commentary** from raw match data.
- Designed for live fan experience during La Liga match days.

### 3. Performance Prediction

- Predict match outcome (Win, Draw, Loss) using:
  - **Random Forest (Scikit-Learn)**
  - (Coming Soon) **PyTorch Neural Network**
- **Trained + deployed with SageMaker**, versioned, and monitored.

### 4. Personalized Content

- **Fetches articles via RSS feeds** (e.g. Managing Madrid).
- Stores user preferences and articles in **DynamoDB**.
- Recommends news based on interests.

---

## Tech Stack

| Layer                  | Tools                                                                 |
|------------------------|-----------------------------------------------------------------------|
| **Languages**          | Python                                                               |
| **ML Libraries**       | scikit-learn, Hugging Face, PyTorch (planned), XGBoost               |
| **API Layer**          | FastAPI, Mangum (for AWS Lambda)                                     |
| **Cloud Infra**        | AWS Lambda, ECR, SageMaker, API Gateway, DynamoDB, S3                |
| **Infra-as-Code**      | Terraform                                                             |
| **Monitoring**         | CloudWatch Dashboards + Alarms                                       |
| **Packaging**          | Docker, Poetry                                                        |
| **CI/CD Ready**        | Makefile-driven DevOps                                               |

---

## Architecture Overview

```
Real-Madrid-AI-Platform/
│
├── services/
│   ├── chatbot/
│   ├── match_commentary/
│   ├── performance_prediction/
│   ├── personalized_content/
│   ├── shared/
│
├── infra/
│   ├── chatbot/
│   ├── match_commentary/
│   ├── performance_prediction/
│   └── personalized_content/
│
├── data/
│   ├── cleaned_laliga_matches.csv
│   ├── real_madrid_facts.jsonl
│
├── notebooks/
│   ├── scrape_data.ipynb
│   └── real-madrid-EDA.ipynb
```

---

## Setup & Usage

### 1. Clone Repo

```bash
git clone https://github.com/Caephas/Real_Madrid_AI_Platform
cd Real_Madrid_AI_Platform
```

### 2. Set Up Python Env

```bash
poetry install
```

### 3. Configure `.env` Files

Each service has its own `.env` for secrets (e.g. API-Football, SageMaker).

Global environment variables for training:

```env
S3_BUCKET=real-madrid-performance-data-bucket
SAGEMAKER_ROLE_ARN=arn:aws:iam::<account>:role/<sagemaker-role>
```

### 4. Deploy Each Service

Each microservice has a `Makefile`:

#### Example: Match Commentary

```bash
cd services/match_commentary
make all
make monitoring
make alerts
```

#### Example: Performance Prediction (SageMaker)

```bash
cd services/performance_prediction
make split-data
make train
make predict
make monitoring
make alerts
```

---

## Monitoring & Alerts

- **Dashboards**: Created via Terraform using CloudWatch widgets
- **Alarms**:
  - High Error Rate
  - High Latency (p90 > 1s)

---

## Endpoints Overview

| Microservice            | Endpoint                                | Method  | Description                        |
|------------------------|------------------------------------------|---------|------------------------------------|
| `chatbot`              | `/chatbot/chat`                          | POST    | Ask Real Madrid facts              |
| `match_commentary`     | `/commentary/{team_id}`                  | GET     | Live match events & commentary     |
| `performance_prediction`| `/prediction/match`                     | POST    | Predict match result               |
| `personalized_content` | `/recommendations/{user_id}`             | GET     | Get personalized articles          |

---

## Coming Soon

### Neural Network Training (PyTorch)

- Train a **DNN with PyTorch** using SageMaker
- Compare with RandomForest for accuracy & latency

---

## Done So Far

Chatbot end-to-end  
Match commentary + API-Football integration  
ML model training + SageMaker deployment  
CloudWatch dashboards & alerts  
Dockerized microservices, Makefiles, Terraform infra  
DynamoDB for content & user data  
