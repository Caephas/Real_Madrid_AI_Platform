# File: tests/test_health.py
"""Integration tests for the /health endpoint."""

from unittest.mock import patch


def test_health_returns_ok(client):
    with (
        patch("app.main.settings.llm_provider", "deepseek"),
        patch("app.main.settings.deepseek_api_key", ""),
    ):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "db" in data
        assert data["llm"] == "not_configured"
        assert data["llm_provider"] == "deepseek"
