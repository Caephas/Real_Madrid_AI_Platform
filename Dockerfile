# Use a Python 3.11-slim base image
FROM python:3.11-slim

LABEL authors="Caephas"

# Set the working directory
WORKDIR /app

# Upgrade pip and install Poetry
RUN pip install --upgrade pip && pip install poetry

# Copy only the Poetry configuration files first to leverage Docker caching
COPY pyproject.toml poetry.lock ./

# Install dependencies using Poetry, skipping dev dependencies
RUN poetry install

# Copy the rest of the application code
COPY . .

# Expose the application port
EXPOSE 8000

# Ensure Python output is unbuffered
ENV PYTHONUNBUFFERED=1

# Define the entry point for the application
CMD ["poetry", "run", "uvicorn", "backend.chatbot.api.chatbot_api:app", "--host", "0.0.0.0", "--port", "8000"]