# File: app/middleware.py
"""CORS and structured logging middleware."""

import logging
import time
import uuid

from fastapi import FastAPI, Request

from app.config import settings

logger = logging.getLogger("app")


def setup_middleware(app: FastAPI) -> None:
    """Attach CORS and request logging middleware to the FastAPI app."""
    from fastapi.middleware.cors import CORSMiddleware

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %d %.0fms [%s]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response
