import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_liveness_probe():
    response = client.get("/livez")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert data["service"] == "mailmind-backend"
    assert "uptime_sec" in data
    assert "timestamp" in data
    assert "trace_id" in data


def test_readiness_probe_deep_checks():
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ready", "degraded"]
    assert "checks" in data
    checks = data["checks"]
    assert "cosmos_db" in checks
    assert "azure_search" in checks
    assert "key_vault" in checks
    assert "azure_openai" in checks
    assert "graph_api" in checks


def test_healthz_summary():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "circuit_breakers" in data
    assert "dependencies" in data


def test_backward_compatible_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "components" in data
    assert "circuit_breakers" in data["components"]
