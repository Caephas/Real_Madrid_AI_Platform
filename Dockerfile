# Use a lightweight Python image
FROM python:3.11-slim

WORKDIR /app

COPY . .

# Set environment variables for Poetry
ENV POETRY_HOME=/opt/poetry
ENV PATH=$POETRY_HOME/bin:$PATH

# Install Python and pip
RUN python3 -m venv $POETRY_HOME && \
    $POETRY_HOME/bin/pip install --upgrade pip setuptools wheel \
poetry==2.0.0

RUN poetry install --no-root

# Expose the application port
EXPOSE 8000
# Command to start the application
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]