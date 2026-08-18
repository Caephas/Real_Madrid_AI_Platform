# Real Madrid AI Platform — System Design

> Architecture, data model, and operational design for the platform.
> Refreshed for the 2026/27 season: DeepSeek LLM, 26-feature model,
> full season hub, and a multi-source data pipeline.

---

## 1. System Context

```mermaid
flowchart LR
    FAN["Fan<br/>(browser)"]
    SYS["Real Madrid AI Platform"]
    DSK["DeepSeek API"]
    AFB["API-Football"]
    RSS["Managing Madrid RSS"]
    FD["football-data.co.uk"]
    FBREF["fbref.com"]

    FAN -->|"predict, chat, news, fixtures"| SYS
    SYS -->|"LLM calls + tool results"| DSK
    SYS -->|"live events & fixtures"| AFB
    SYS -->|"article ingestion"| RSS
    SYS -.->|"offline season fetch"| FD
    SYS -.->|"offline full-fidelity scrape"| FBREF
```

**Actors**

- **Fan** — uses the SPA for predictions, chat, live commentary, news.
- **Operator** — runs the offline pipeline (`make pipeline`), monitors
  `GET /health`, retrains as seasons complete.

---

## 2. Container Diagram

```mermaid
flowchart TB
    subgraph Client
        SPA["Vite + React SPA<br/>:8080"]
    end

    subgraph Backend["FastAPI app :8000"]
        API["REST + SSE endpoints"]
        AGENT["Chatbot agent loop"]
        PRED["Prediction service"]
        FIX["Fixture/season service"]
        COMM["Commentary service"]
        CONT["Content service"]
    end

    PG[("PostgreSQL 16<br/>:5432/5433")]
    MODELS[("models/ volume")]
    DSK["DeepSeek API"]
    AFB["API-Football"]
    RSS["RSS feed"]

    SPA -->|HTTP / SSE| API
    API --> AGENT & PRED & FIX & COMM & CONT
    AGENT --> DSK
    AGENT --> PRED & COMM & CONT
    PRED --> MODELS
    PRED & COMM & CONT & AGENT --> PG
    FIX --> AFB
    COMM --> AFB
    CONT --> RSS
```

**Key decisions**

- **Monolith FastAPI** with modular packages (`chatbot`, `prediction`,
  `commentary`, `content`, `fixtures`) — appropriate for a single-host
  personal platform; keeps ops trivial (one process).
- **SSE streaming** for chat (`POST /chat/stream`) — token-by-token UX without
  WebSocket complexity.
- **PostgreSQL** for match events, articles, users, chat history, and live
  team rolling stats (the prediction lookup table).

---

## 3. Backend Modules

```mermaid
flowchart LR
    subgraph app/
        MAIN["main.py — lifespan, scheduler, health"]
        CFG["config.py — Pydantic settings"]
        DB["database.py — engine/session"]
        MODELS["models.py — ORM"]
        CHAT["chatbot/"]
        PRED["prediction/"]
        COMM["commentary/"]
        CONT["content/"]
        FIX["fixtures.py + fixtures JSON"]
    end

    MAIN --> CHAT & PRED & COMM & CONT & FIX
    CHAT --> PRED & COMM & CONT
    CHAT & PRED & COMM & CONT --> DB --> MODELS
    PRED --> FIX
```

### Chatbot agent loop

```mermaid
sequenceDiagram
    participant U as User
    participant R as /chat/stream
    participant A as Agent loop
    participant L as DeepSeek
    participant T as Tools

    U->>R: message + conversation_id
    R->>A: run_agent_stream(history)
    loop up to 5 iterations
        A->>L: messages + tool definitions
        alt tool call requested
            L-->>A: tool_calls
            A->>T: execute (predict/commentary/news/fixtures)
            T-->>A: real data
        else final answer
            L-->>A: streamed deltas
            A-->>R: delta events (SSE)
        end
    end
    R-->>U: done + conversation_id
```

- Conversation history is persisted in `chat_messages` and replayed into the
  prompt (last 8 messages) so the agent remembers context.
- Empty LLM responses (reasoning-heavy models) trigger one retry before
  giving up — prevents blank answers.
- Provider abstraction: `DeepSeekProvider` (default), `OllamaProvider`,
  `GeminiProvider`, selected via `LLM_PROVIDER`.

---

## 4. Data Model

```mermaid
erDiagram
    ARTICLES {
        str article_id PK
        str category
        str title
        str link
        datetime published
        text content
        str image_url
        str author
    }
    USERS {
        str user_id PK
        json preferences
        datetime created_at
    }
    MATCH_EVENTS {
        str id PK
        str team
        str type
        str player
        int minute
        json raw_event
    }
    TEAM_STATS {
        str team_name PK
        float gf_rolling
        float ga_rolling
        float sh_rolling
        float sot_rolling
        float dist_rolling
        float fk_rolling
        float pk_rolling
        float pkatt_rolling
        float xg_rolling
        float xga_rolling
        float poss_rolling
        datetime updated_at
    }
    CHAT_MESSAGES {
        str id PK
        str conversation_id
        str role
        text content
        datetime created_at
    }

    USERS ||--o{ CHAT_MESSAGES : "owns"
```

**Design notes**

- `team_stats` is the prediction hot-path table: one row per team with
  5-game rolling averages (11 stats). Inference does O(1) lookups.
- `chat_messages` enables conversation memory without a vector store.
- Alembic migrations are versioned (`migrations/versions/`); the app also
  calls `create_all` as a fallback for fresh installs.

---

## 5. Prediction Feature Pipeline

```mermaid
flowchart LR
    RAW[("raw matches CSV")]
    CLEAN["clean.py<br/>normalize names → encode →<br/>5-game rolling (closed-left) →<br/>opponent merge → split"]
    TRAIN["train.py<br/>SMOTE → XGBoost (early stop)<br/>+ RandomForest → select by log loss"]
    ARTIFACTS[("models/: pkl + metrics + importance + mappings")]
    STATS[("team_stats table")]
    INFER["features.py<br/>26-feature vector"]

    RAW --> CLEAN --> TRAIN --> ARTIFACTS
    RAW -->|update_team_stats.py| STATS
    ARTIFACTS --> INFER
    STATS --> INFER
```

**The 26 features** (single source of truth: `app/prediction/features.py`):

1. Basic: `venue_code`, `opp_code`, `hour`, `day_code`
2. Real Madrid rolling (5-game): `gf`, `ga`, `sh`, `sot`, `dist`, `fk`, `pk`,
   `pkatt`, `xg`, `xga`, `poss`
3. Opponent rolling: same 11, prefixed `opp_`

Rolling windows use `closed='left'` so the current match's stats never leak
into its own features. The split is temporal (last 2 seasons = test).

**Graceful degradation** — new/promoted teams (e.g. Málaga, Oviedo) get a
stable fallback opponent code and league-average stats until their data
exists, so predictions never hard-fail.

---

## 6. Data Collection

```mermaid
flowchart TB
    subgraph Offline["Offline (make pipeline / fetch_season)"]
        FD["football-data.co.uk<br/>complete season, no key"]
        AFB["API-Football<br/>full stats when covered"]
        FBREF["fbref via scrape.py<br/>gold standard, resumable"]
    end
    MERGE["merge_into_raw<br/>dedupe (date, team)"]
    RAW[("la_liga_10_seasons.csv")]

    FD --> MERGE
    AFB --> MERGE
    FBREF --> MERGE
    MERGE --> RAW
```

- `fetch_season.py` fills xG/possession/etc. with league-average priors when
  the source lacks them, so downstream rolling features stay on scale.
- `scrape.py` checkpoints per team-season (`data/raw/partial/`) for resumable
  full-fidelity pulls.

---

## 7. Fixtures & Season Hub

```mermaid
flowchart LR
    STATIC["app/fixtures_2026_27.json<br/>38 matchdays"]
    OVERRIDE["data/fixtures_2026_27.json<br/>(optional override)"]
    API["API-Football<br/>fixtures + results"]
    CACHE["6h TTL cache"]
    SVC["fixtures.py<br/>merge by matchday"]
    ENDPOINTS["/season /next-match /fixtures /results"]

    STATIC --> SVC
    OVERRIDE --> SVC
    API --> CACHE --> SVC
    SVC --> ENDPOINTS
```

The static schedule guarantees offline availability; API-Football enriches
kickoff times and finished-match results when the key is configured.

---

## 8. Security & Operations

- **Secrets**: `.env` is gitignored. Keys: `DEEPSEEK_API_KEY`,
  `API_FOOTBALL_KEY`, optional `GEMINI_API_KEY`.
- **LLM keys** live only server-side; the frontend never sees them.
- **Dependency hygiene**: ruff + black enforced via `make lint`; 62 pytest
  tests plus frontend vitest; CI-friendly (`make test` exits non-zero on
  failure).
- **Monitoring**: `GET /health` reports DB + LLM connectivity. Request
  middleware logs method, path, status, latency, and a request ID.
- **Scheduler** (APScheduler): RSS fetch every 6h, team-stats staleness check
  every 24h — both fail soft (logged, non-fatal).

---

## 9. Deployment

```mermaid
flowchart TB
    subgraph Docker["Docker Compose"]
        PG["postgres:16"]
        OLL["ollama (optional, local LLM)"]
        APP["app container<br/>uvicorn :8000"]
    end
    FE["frontend dev server :8080"]
    VOL[("models/ volume")]

    APP --> PG
    APP --> VOL
    APP -.-> OLL
    FE --> APP
```

Local dev (recommended):

```bash
make setup
make dev          # backend :8000
cd frontend && npm run dev   # frontend :8080
```

Docker:

```bash
docker compose up --build
```

---

## 10. Future Work

- Full API-Football season mapping in `fetch_season.py` (when a season is
  covered there) for real xG/possession on every pulled season.
- Model calibration (temperature scaling) for sharper W/D/L probabilities.
- User auth + per-user chat history isolation.
- Historical fixtures/results page (season standings table).
