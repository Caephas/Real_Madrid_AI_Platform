# Real Madrid AI Platform — System Design

## 1. System Context

An AI-powered platform for Real Madrid fans. Four capabilities: agentic chatbot, match outcome prediction, live commentary, and personalized news. Runs **fully local** via Docker containers — zero cloud dependency.

```mermaid
graph TB
    subgraph Actors
        FAN["Fan (Browser)"]
        DEV["Developer / Operator"]
    end

    subgraph "Real Madrid AI Platform (Docker Compose)"
        API["FastAPI Backend<br/>(Docker Container)"]
        DB["PostgreSQL<br/>(Docker Container)"]
        LLM["Ollama<br/>(Docker Container)"]
    end

    subgraph "External APIs (optional)"
        GEM["Gemini API<br/>(optional remote LLM)"]
        AF["API-Football<br/>(Live Match Data)"]
        RSS["Managing Madrid RSS<br/>(News Articles)"]
        FB["fbref.com<br/>(Historical Stats)"]
    end

    FAN -->|"HTTP"| API
    DEV -->|"CLI: pipeline, docker-compose"| API
    API --> DB
    API --> LLM
    API -.->|"optional"| GEM
    API --> AF
    API --> RSS
    DEV -->|"scrape (offline)"| FB
```

---

## 2. Container Diagram

```mermaid
graph TB
    subgraph "Docker Compose Network"
        subgraph "app (port 8000)"
            API["FastAPI + Uvicorn<br/>Backend Monolith"]
            SCHED["APScheduler<br/>(RSS fetch every 6h)"]
        end

        subgraph "db (port 5432)"
            PG["PostgreSQL 16<br/>match_events, articles,<br/>users, team_stats"]
        end

        subgraph "ollama (port 11434)"
            OLL["Ollama Server<br/>llama3 / mistral"]
        end
    end

    subgraph "Frontend (port 5173)"
        FE["Vite + React<br/>(npm run dev or container)"]
    end

    subgraph "External APIs"
        AF["API-Football"]
        RSS["RSS Feed"]
    end

    subgraph "Local Filesystem (volumes)"
        VOL_MODELS["./models/<br/>xgboost_model.pkl<br/>opponent_mapping.json<br/>venue_mapping.json"]
        VOL_DATA["./data/<br/>raw + processed CSVs"]
    end

    FE -->|"HTTP"| API
    API --> PG
    API --> OLL
    API -->|"read model files"| VOL_MODELS
    API --> AF
    API --> RSS
    SCHED -.->|"trigger"| API

    style API stroke:#0a0,stroke-width:3px
    style PG stroke:#336,stroke-width:2px
    style OLL stroke:#f60,stroke-width:2px
```

### Cost: **$0/mo** (runs on your machine)

---

## 3. Component Diagram (Backend)

```mermaid
graph TB
    subgraph "FastAPI Application"
        MAIN["main.py<br/>(Uvicorn entrypoint,<br/>lifespan: scheduler + model warmup)"]
        MW["middleware.py<br/>(CORS, request logging, errors)"]
        CFG["config.py<br/>(Pydantic Settings)"]
        DB_MOD["database.py<br/>(SQLAlchemy engine + session)"]

        subgraph "chatbot/"
            C_R["router.py<br/>POST /chat"]
            C_A["agent.py<br/>tool-calling loop"]
            C_LLM["llm_provider.py<br/>GeminiProvider | OllamaProvider"]
            C_T["tools.py<br/>tool definitions + executor"]
        end

        subgraph "prediction/"
            P_R["router.py<br/>POST /predict"]
            P_M["model.py<br/>load from ./models/ volume"]
            P_F["features.py<br/>feature vector builder"]
            P_MAP["mappings.py<br/>opponent/venue code maps"]
        end

        subgraph "commentary/"
            CO_R["router.py<br/>GET /commentary/{team_id}"]
            CO_AF["api_football.py<br/>API client + retry"]
            CO_G["generator.py<br/>event → text"]
        end

        subgraph "content/"
            CN_R["router.py<br/>GET /articles<br/>GET /recommendations/{user_id}"]
            CN_RSS["rss.py<br/>fetch + categorize"]
            CN_DB["crud.py<br/>article/user CRUD via SQLAlchemy"]
        end
    end

    MAIN --> MW
    MAIN --> C_R
    MAIN --> P_R
    MAIN --> CO_R
    MAIN --> CN_R
    MAIN --> DB_MOD
    C_R --> C_A --> C_LLM
    C_A --> C_T
    C_T -.->|"tool: predict_match"| P_R
    C_T -.->|"tool: get_live_commentary"| CO_R
    C_T -.->|"tool: get_articles"| CN_R
    C_T -.->|"tool: get_team_stats"| DB_MOD
    P_R --> P_M
    P_R --> P_F --> P_MAP
    CN_DB --> DB_MOD
```

---

## 4. Agent Architecture

```mermaid
sequenceDiagram
    participant U as User
    participant R as /chat Router
    participant A as Agent Loop
    participant LLM as Ollama / Gemini
    participant T as Tool Executor
    participant P as prediction/
    participant CO as commentary/
    participant CN as content/

    U->>R: POST /chat {"prompt": "Will we beat Atletico?"}
    R->>A: run_agent(prompt, tools)

    loop Max 5 iterations
        A->>LLM: chat(messages, tool_schemas)
        LLM-->>A: tool_call: predict_match("Atletico Madrid", "home", "2025-04-20")
        A->>T: execute("predict_match", args)
        T->>P: predict(opponent, venue, date)
        P-->>T: {"win": 0.62, "draw": 0.24, "loss": 0.14}
        T-->>A: tool_result

        A->>LLM: chat(messages + tool_result, tool_schemas)
        LLM-->>A: tool_call: get_articles("Match Previews")
        A->>T: execute("get_articles", args)
        T->>CN: get_articles(category)
        CN-->>T: [{"title": "Atletico preview..."}]
        T-->>A: tool_result

        A->>LLM: chat(messages + tool_results, tool_schemas)
        LLM-->>A: final_text (no more tool calls)
    end

    A-->>R: "62% win probability. RM on a 5-game streak..."
    R-->>U: {"response": "..."}
```

---

## 5. LLM Provider Swap

```mermaid
classDiagram
    class LLMProvider {
        <<Protocol>>
        +chat(messages, tools) LLMResponse
    }

    class LLMResponse {
        +text: str | None
        +tool_calls: list~ToolCall~
    }

    class ToolCall {
        +id: str
        +name: str
        +args: dict
    }

    class GeminiProvider {
        -api_key: str
        +chat(messages, tools) LLMResponse
    }

    class OllamaProvider {
        -base_url: str
        -model_name: str
        +chat(messages, tools) LLMResponse
    }

    LLMProvider <|.. GeminiProvider : implements
    LLMProvider <|.. OllamaProvider : implements
    LLMResponse --> ToolCall
```

```
LLM_PROVIDER=ollama  →  OllamaProvider(base_url="http://ollama:11434", model="llama3")
LLM_PROVIDER=gemini  →  GeminiProvider(api_key=GEMINI_API_KEY)
```

Default: **Ollama** (fully local, no API key required).

---

## 6. Data Pipeline

```mermaid
flowchart LR
    subgraph "1. Scrape"
        FB["fbref.com"] -->|"requests + BS4"| RAW["data/raw/<br/>la_liga.csv"]
    end

    subgraph "2. Clean"
        RAW -->|"pipeline/clean.py"| PROC["data/processed/<br/>cleaned_laliga.csv"]
    end

    subgraph "3. Train"
        PROC -->|"pipeline/train.py"| MODEL["models/<br/>xgboost_model.pkl"]
        PROC -->|"pipeline/train.py"| MAPS["models/<br/>*_mapping.json"]
        PROC -->|"pipeline/update_team_stats.py"| STATS["PostgreSQL<br/>team_stats table"]
    end

    subgraph "4. Serve"
        MODEL -->|"volume mount"| API["FastAPI container<br/>loads on startup"]
        MAPS -->|"volume mount"| API
        STATS -->|"SQL query"| API
    end

    style MODEL stroke:#f90,stroke-width:2px
    style API stroke:#0a0,stroke-width:2px
```

No S3 upload step. Model files are mounted directly into the container via Docker volumes.

---

## 7. API Design

| Method | Path | Module | Description |
|--------|------|--------|-------------|
| `POST` | `/chat` | chatbot | Agent processes prompt, may call tools |
| `POST` | `/predict` | prediction | W/D/L probabilities for a match |
| `GET` | `/commentary/{team_id}` | commentary | Live events + generated commentary |
| `GET` | `/articles` | content | List articles, optional `?category=` |
| `GET` | `/recommendations/{user_id}` | content | Personalized articles |
| `GET` | `/health` | root | Health check (DB + Ollama connectivity) |

### Request/Response Schemas

```mermaid
classDiagram
    class ChatRequest {
        +prompt: str
    }
    class ChatResponse {
        +response: str
        +tools_used: list~str~
    }

    class PredictRequest {
        +opponent: str
        +venue: "home" | "away"
        +date: str
    }
    class PredictResponse {
        +win: float
        +draw: float
        +loss: float
    }

    class CommentaryResponse {
        +team_id: int
        +match_status: str
        +events: list~CommentaryEvent~
    }
    class CommentaryEvent {
        +minute: int
        +type: str
        +player: str
        +commentary: str
    }
```

---

## 8. Data Model (PostgreSQL)

```mermaid
erDiagram
    match_events {
        uuid id PK
        varchar team
        varchar type
        varchar player
        int minute
        jsonb raw_event
        timestamp created_at
    }

    articles {
        varchar article_id PK
        varchar category
        varchar title
        varchar link
        timestamp published
        text content
        varchar author
        timestamp fetched_at
    }

    users {
        varchar user_id PK
        jsonb preferences
        timestamp created_at
    }

    team_stats {
        varchar team_name PK
        float gf_rolling
        float ga_rolling
        float sh_rolling
        float sot_rolling
        float dist_rolling
        float fk_rolling
        float pk_rolling
        float pkatt_rolling
        timestamp updated_at
    }

    users ||--o{ articles : "preferences match category"
```

### Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| `articles` | `ix_articles_category` | Filter by category |
| `articles` | `ix_articles_published` | Sort by recency |
| `match_events` | `ix_events_team` | Filter by team |
| `team_stats` | PK on `team_name` | Feature lookup at inference |

---

## 9. Docker Compose Architecture

```mermaid
graph TB
    subgraph "docker-compose.yml"
        subgraph "app"
            API["FastAPI<br/>Port: 8000<br/>Depends: db, ollama"]
        end
        subgraph "db"
            PG["PostgreSQL 16<br/>Port: 5432<br/>Volume: pgdata"]
        end
        subgraph "ollama"
            OLL["Ollama Server<br/>Port: 11434<br/>Volume: ollama_models"]
        end
        subgraph "frontend"
            FE["Vite Dev Server<br/>Port: 5173<br/>Depends: app"]
        end
    end

    subgraph "Volumes"
        V1["pgdata<br/>(persistent DB)"]
        V2["ollama_models<br/>(LLM weights)"]
        V3["./models/<br/>(ML artifacts, bind mount)"]
        V4["./data/<br/>(pipeline data, bind mount)"]
    end

    PG --> V1
    OLL --> V2
    API --> V3
    API --> V4
    FE -->|"proxy to :8000"| API
    API --> PG
    API --> OLL
```

```yaml
# docker-compose.yml (conceptual)
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: real_madrid
      POSTGRES_USER: rmadmin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_models:/root/.ollama
    ports:
      - "11434:11434"

  app:
    build: .
    environment:
      DATABASE_URL: postgresql://rmadmin:${DB_PASSWORD}@db:5432/real_madrid
      LLM_PROVIDER: ollama
      OLLAMA_BASE_URL: http://ollama:11434
      MODEL_DIR: /app/models
    volumes:
      - ./models:/app/models:ro
      - ./data:/app/data:ro
    ports:
      - "8000:8000"
    depends_on:
      - db
      - ollama

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - app

volumes:
  pgdata:
  ollama_models:
```

---

## 10. Startup & Initialization

```mermaid
sequenceDiagram
    participant DC as docker-compose up
    participant PG as PostgreSQL
    participant OLL as Ollama
    participant APP as FastAPI

    DC->>PG: Start container
    DC->>OLL: Start container
    PG-->>DC: Ready (port 5432)
    OLL-->>DC: Ready (port 11434)
    DC->>APP: Start container (depends_on: db, ollama)

    APP->>APP: Lifespan startup
    APP->>PG: Run Alembic migrations (create tables)
    APP->>APP: Load XGBoost model from ./models/
    APP->>APP: Load opponent/venue mappings from ./models/
    APP->>APP: Start APScheduler (RSS fetch every 6h)
    APP-->>DC: Ready (port 8000)

    DC->>DC: Start frontend (depends_on: app)
```

---

## 11. Model Serving (Local)

```python
# No S3. No boto3. Just filesystem.
import joblib
from pathlib import Path

_model = None

def get_model(model_dir: str = "/app/models") -> object:
    global _model
    if _model is None:
        path = Path(model_dir) / "xgboost_model.pkl"
        _model = joblib.load(path)
    return _model
```

Model is loaded **once** at startup via FastAPI lifespan, cached in-process. No cold starts, no S3 downloads. Docker volume mount makes `./models/` available at `/app/models` inside the container.

---

## 12. Deployment Flow

```mermaid
sequenceDiagram
    participant D as Developer
    participant MK as Makefile
    participant DC as docker-compose

    Note over D,DC: First-time setup
    D->>MK: make setup
    MK->>DC: docker-compose up -d db ollama
    MK->>MK: ollama pull llama3
    MK->>DC: docker-compose up -d app frontend

    Note over D,DC: Pipeline execution
    D->>MK: make pipeline
    MK->>MK: python -m pipeline.scrape
    MK->>MK: python -m pipeline.clean
    MK->>MK: python -m pipeline.train
    MK->>MK: python -m pipeline.update_team_stats

    Note over D,DC: Restart to pick up new model
    D->>MK: make restart
    MK->>DC: docker-compose restart app
```

---

## 13. Project Structure (Updated)

```
Real_Madrid_AI_Platform/
├── app/
│   ├── __init__.py
│   ├── main.py               # Uvicorn entrypoint, lifespan, scheduler
│   ├── config.py              # Pydantic Settings (DATABASE_URL, LLM_PROVIDER, etc.)
│   ├── database.py            # SQLAlchemy engine, session, Base
│   ├── models.py              # SQLAlchemy ORM models (all tables)
│   ├── middleware.py           # CORS, structured logging
│   ├── chatbot/
│   │   ├── router.py
│   │   ├── agent.py
│   │   ├── llm_provider.py
│   │   └── tools.py
│   ├── prediction/
│   │   ├── router.py
│   │   ├── model.py           # Load from filesystem, no S3
│   │   ├── features.py
│   │   └── mappings.py
│   ├── commentary/
│   │   ├── router.py
│   │   ├── api_football.py
│   │   └── generator.py
│   └── content/
│       ├── router.py
│       ├── rss.py
│       └── crud.py            # SQLAlchemy queries
├── pipeline/
│   ├── scrape.py
│   ├── clean.py
│   ├── train.py
│   └── update_team_stats.py
├── migrations/                 # Alembic
│   ├── env.py
│   └── versions/
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── data/
├── models/
├── tests/
│   ├── conftest.py
│   └── ...
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
├── alembic.ini
├── .env.example
└── README.md
```

---

## 14. Security Considerations

| Concern | Mitigation |
|---------|------------|
| DB credentials | `.env` file (gitignored), `DB_PASSWORD` env var |
| Gemini API key (optional) | `.env` file, only needed if `LLM_PROVIDER=gemini` |
| API-Football key | `.env` file |
| CORS | Restrict `allow_origins` to `http://localhost:5173` |
| SQL injection | SQLAlchemy parameterized queries, Pydantic input validation |
| Agent runaway | Max 5 tool-call iterations, request timeout middleware |
| Container isolation | App runs as non-root user in Dockerfile |

---

## 15. Technology Stack

| Layer | Technology | Replaces |
|-------|-----------|----------|
| Runtime | Docker + docker-compose | AWS Lambda + API Gateway |
| Database | PostgreSQL 16 | DynamoDB |
| ORM | SQLAlchemy + Alembic | boto3 DynamoDB resource |
| Model storage | Local filesystem (Docker volume) | S3 |
| LLM | Ollama (local) / Gemini (optional) | Gemini-only |
| Scheduling | APScheduler (in-process) | EventBridge |
| Monitoring | Structured logging (JSON) | CloudWatch |
| IaC | docker-compose.yml | Terraform |
| Frontend | Vite + React | — |

---

## 16. Future Considerations

| Enhancement | Complexity | Value |
|-------------|-----------|-------|
| Nginx reverse proxy | Low | SSL termination, rate limiting |
| Prometheus + Grafana | Medium | Metrics dashboards |
| Redis caching | Low | Cache predictions, API-Football responses |
| User auth (JWT) | Medium | Real user preferences |
| CI/CD (GitHub Actions) | Low | Auto-test on push |
| Cloud deployment option | Medium | Deploy same containers to ECS/Fly.io/Railway |
| Multi-league support | Medium | Generalize beyond Real Madrid |
