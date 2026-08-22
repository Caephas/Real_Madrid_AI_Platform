# ============================================
# Real Madrid AI Platform
# ============================================

FROM python:3.11-slim AS builder

RUN pip install --no-cache-dir hatchling

WORKDIR /build
COPY pyproject.toml .
COPY README.md .
COPY app/ ./app/
COPY pipeline/ ./pipeline/
RUN pip install --no-cache-dir --prefix=/install .

# -------------------------------------------

FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY models/ ./models/
COPY data/raw/la_liga_10_seasons.csv ./data/raw/la_liga_10_seasons.csv

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
