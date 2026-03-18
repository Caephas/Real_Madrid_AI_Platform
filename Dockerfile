# ============================================
# Real Madrid AI Platform
# ============================================

FROM python:3.11-slim AS builder

RUN pip install --no-cache-dir hatchling

WORKDIR /build
COPY pyproject.toml .
COPY app/ ./app/
COPY pipeline/ ./pipeline/
RUN pip install --no-cache-dir --prefix=/install .

# -------------------------------------------

FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /install /usr/local

WORKDIR /app
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
