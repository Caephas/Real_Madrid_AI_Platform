# File: tests/test_health.py
"""Integration tests for the /health endpoint."""

def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "db" in data
    assert "ollama" in data
