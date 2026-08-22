# Deployment Guide (Free Tier)

The platform is deployed in three parts, each with a generous free tier:

```mermaid
flowchart LR
    U[Browser] --> H[Firebase Hosting<br/>static SPA + assets]
    H --> R[Cloud Run<br/>FastAPI container]
    R --> N[(Neon Postgres<br/>free tier)]
    R --> G[Gemini API<br/>vision]
    R --> D[DeepSeek API<br/>chat LLM]
```

| Component | Service | Free allowance | Cost risk |
|---|---|---|---|
| Frontend | Firebase Hosting (Spark) | 10 GB storage, 360 MB/day transfer | None |
| Backend | Cloud Run | 2M requests/mo, 180K vCPU-sec, 360K GiB-sec | Requires billing account, but $0 at hobby traffic |
| Database | Neon (free tier) | 0.5 GB storage, ~190 compute hours/mo | None |
| Vision | Gemini API | Free tier available via AI Studio key | Pay per request beyond free quota |
| Chat | DeepSeek | Pay-per-token (cheap) | Minimal |

The frontend talks to the backend **directly** (cross-origin) rather than via
Hosting rewrites, because Hosting rewrites to Cloud Run force the paid Blaze
plan. CORS is already enabled on the backend (`CORS_ORIGINS=*` by default).

## Prerequisites

- `firebase` CLI, logged in: `firebase login`
- `gcloud` CLI, logged in with the **same Google account** that owns the
  Firebase project: `gcloud auth login`
- A Neon account (free) for Postgres

## 1. Firebase project

Already created for this repo: **`real-madrid-ai`**
(`.firebaserc` points at it). Create a replacement with:

```bash
firebase projects:create real-madrid-ai --display-name "Real Madrid AI"
```

Cloud Run needs billing enabled on the project (Firebase "Blaze" plan). This
does not mean you pay — the free allowances above cover normal hobby traffic.
Enable it in the Firebase console: **Project settings → Usage and billing →
Modify plan**. A card is required, but you are only charged if usage exceeds
the free tier.

## 2. Postgres (Neon, free)

1. Sign up at [neon.tech](https://neon.tech) and create a project.
2. Copy the **connection string** (the `psql`/driver one, e.g.
   `postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/real_madrid?sslmode=require`).

Neon's pooled connection string (`-pooler`) is fine for the app; use the
direct one for migrations if the pooler gives `prepared statement` errors.

## 3. Backend secrets

Create `deploy/env.json` (gitignored — never commit it):

```json
{
  "DATABASE_URL": "postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/real_madrid?sslmode=require",
  "DEEPSEEK_API_KEY": "sk-...",
  "GEMINI_API_KEY": "AQ....",
  "GEMINI_MODEL": "gemini-3.6-flash",
  "CORS_ORIGINS": "*"
}
```

Optional extras: `API_FOOTBALL_KEY`, `API_FOOTBALL_BASE_URL`,
`LLM_PROVIDER`.

## 4. Deploy

Enable the required APIs once (billing must be on for the project):

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project real-madrid-ai
```

Deploy the backend first so you get its URL:

```bash
make deploy-backend
```

This builds the Dockerfile (Python + ffmpeg + yt-dlp) with Cloud Build and
serves it at `https://real-madrid-api-<hash>-ew.a.run.app`. If the container
image build is slow, the first deploy can take several minutes.

Then deploy the frontend, pointing it at the backend:

```bash
make deploy-frontend API_BASE=https://real-madrid-api-<hash>-ew.a.run.app
```

Your site is live at `https://real-madrid-ai.web.app`.

The current production backend is
`https://real-madrid-api-979352484663.europe-west1.run.app`.

Run migrations against the production database (do this before the first
backend request):

```bash
make deploy-db DATABASE_URL=postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/real_madrid?sslmode=require
```

Or run everything in order:

```bash
make deploy API_BASE=https://real-madrid-api-<hash>-ew.a.run.app DATABASE_URL=postgresql://...
```

## Verification

- `curl https://real-madrid-ai.web.app` returns the SPA.
- `curl https://real-madrid-api-<hash>-ew.a.run.app/health` returns
  `{"status":"ok","db":"connected","llm":"connected",...}`.
- Open the site, check Dashboard, Fixtures, History, and Call Review.

## Operational notes

- **Call Review jobs** run in a background thread after the request returns.
  Cloud Run keeps an instance alive for ~15 min after its last request, which
  comfortably covers the 10-minute job timeout. Under heavy parallel load the
  instance can be recycled mid-job; jobs are then marked failed and can be
  re-run.
- **The container listens on `$PORT`** (Cloud Run injects `8080`); it falls
  back to `8000` locally. Never hardcode the port in the CMD.
- **`data/raw/la_liga_10_seasons.csv` is baked into the image** — it powers
  `/standings`, `/form`, `/history`, and `/h2h`. Redeploy after a `make
  refresh` to publish the latest table. (`.gcloudignore`/`.dockerignore`
  re-include it with the parent-directory trick.)
- **Uploads are ephemeral.** `data/uploads/` lives on the instance's local
  disk, so job frames and videos disappear when the container is replaced.
  Job metadata and verdicts persist in Postgres.
- **Memory:** the container is set to 2 GiB to fit a 200 MB upload plus the
  downloaded 720p clip plus ffmpeg working sets.
- **Scaling cap:** `--max-instances 1` keeps cost predictable on the free
  tier. If you expect concurrent users, raise it and re-check the free-tier
  allowances.
- **Custom domain:** attach one under Hosting in the Firebase console (free
  SSL). Update `CORS_ORIGINS` to your domain afterwards.

## Costs at a glance

At hobby traffic (a few hundred requests/day), the expected bill is **$0**:
Hosting and Neon are free, Cloud Run stays inside its monthly free allowance,
and Gemini/DeepSeek usage is pennies or covered by their free tiers.
