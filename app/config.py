# File: app/config.py
"""Centralized configuration. All env vars loaded once via Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql://rmadmin:changeme@localhost:5432/real_madrid"

    # LLM
    llm_provider: str = "deepseek"  # "deepseek" | "ollama" | "gemini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"

    # API-Football
    api_football_key: str = ""
    api_football_base_url: str = "https://v3.football.api-sports.io/"

    # Model
    model_dir: str = "./models"

    # Real Madrid team ID in API-Football
    real_madrid_team_id: int = 541


settings = Settings()
