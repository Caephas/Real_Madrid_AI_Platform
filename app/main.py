# File: app/main.py
"""FastAPI application entrypoint with lifespan for startup/shutdown tasks."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import engine, Base
from app.middleware import setup_middleware
from app.prediction.model import load_model
from app.prediction.mappings import load_mappings
from app.prediction.router import router as prediction_router
from app.content.router import router as content_router
from app.content.rss import fetch_and_store_articles
from app.commentary.router import router as commentary_router
from app.chatbot.router import router as chatbot_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: run migrations, load model, start scheduler. Shutdown: cleanup."""
    logger.info("Starting Real Madrid AI Platform")

    # Create tables (use Alembic in prod, this is a fallback)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    # Load ML model and mappings from ./models/ volume
    try:
        load_model()
        load_mappings()
        logger.info("ML model and mappings loaded from %s", settings.model_dir)
    except FileNotFoundError as e:
        logger.warning("Model/mappings not found: %s. /predict will fail until `make pipeline` is run.", e)

    # Start APScheduler for periodic RSS fetch
    from datetime import datetime
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fetch_and_store_articles, "interval", hours=6, id="rss_fetch",
        next_run_time=datetime.now(),  # run immediately on startup
    )
    scheduler.start()
    logger.info("APScheduler started: RSS fetch every 6 hours")

    yield

    scheduler.shutdown(wait=False)
    logger.info("Shutting down")


app = FastAPI(
    title="Real Madrid AI Platform",
    description="AI-powered platform for Real Madrid fans",
    version="1.0.0",
    lifespan=lifespan,
)

setup_middleware(app)
app.include_router(prediction_router)
app.include_router(content_router)
app.include_router(commentary_router)
app.include_router(chatbot_router)


@app.get("/health")
def health_check():
    """Verify backend, database, and (optionally) Ollama connectivity."""
    from sqlalchemy import text
    from app.database import SessionLocal

    # Check DB
    db_status = "disconnected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception:
        pass

    # Check Ollama
    ollama_status = "skipped"
    if settings.llm_provider == "ollama":
        import httpx

        try:
            r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3)
            ollama_status = "connected" if r.status_code == 200 else "error"
        except Exception:
            ollama_status = "disconnected"

    return {"status": "ok", "db": db_status, "ollama": ollama_status}
