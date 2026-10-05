import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app, rate_limiter, ServiceUnavailableException


class TestHealthAndErrorHandling:
    """Test suite for health probes, custom error handlers (422, 429, 503, 404), and DLQ/Quarantine APIs."""

    def test_health_check_endpoint(self, client):
        """Test /api/health returns comprehensive status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "dlq_pending_count" in data["components"]

    def test_liveness_probe(self, client):
        """Test Kubernetes liveness probe /api/health/liveness."""
        response = client.get("/api/health/liveness")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_readiness_probe(self, client):
        """Test Kubernetes readiness probe /api/health/readiness."""
        response = client.get("/api/health/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data

    def test_422_validation_error_handler(self, client):
        """Test 422 Unprocessable Entity custom error handler with malformed email payload."""
        # Missing required 'body' and invalid types
        bad_payload = {
            "id": 12345,  # should be str
            "sender": "not-an-email",
            # missing subject, body, received_at
        }
        response = client.post("/api/process-email", json=bad_payload)
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "Validation Error"
        assert data["status_code"] == 422
        assert "detail" in data
        assert "timestamp" in data
        assert data["path"] == "/api/process-email"

    def test_404_not_found_error_handler(self, client):
        """Test 404 custom error handler for non-existent resources."""
        response = client.get("/api/emails/non-existent-email-id-999")
        assert response.status_code == 404
        data = response.json()
        assert data["status_code"] == 404
        assert "not found" in data["detail"].lower()

    def test_429_rate_limiting_middleware(self, client, monkeypatch):
        """Test sliding-window rate limiting middleware returns HTTP 429 when threshold exceeded."""
        # Temporarily configure rate limiter to 3 requests per minute for this test
        monkeypatch.setattr(rate_limiter, "requests_per_minute", 3)

        # 3 requests should pass
        for _ in range(3):
            res = client.get("/api/emails")
            assert res.status_code == 200

        # 4th request must be rate-limited (HTTP 429)
        res_4 = client.get("/api/emails")
        assert res_4.status_code == 429
        data = res_4.json()
        assert data["error"] == "Too Many Requests"
        assert data["status_code"] == 429
        assert "Retry-After" in res_4.headers
        assert "X-RateLimit-Limit" in res_4.headers

    def test_rate_limiting_bypass_for_health_probes(self, client, monkeypatch):
        """Test health probe endpoints are exempt from rate limiting."""
        monkeypatch.setattr(rate_limiter, "requests_per_minute", 1)

        # First regular request consumes the quota
        res1 = client.get("/api/emails")
        assert res1.status_code == 200

        # Subsequent health probe requests must still succeed (200 OK)
        for _ in range(5):
            res_health = client.get("/api/health")
            assert res_health.status_code == 200

            res_live = client.get("/api/health/liveness")
            assert res_live.status_code == 200

    def test_503_service_unavailable_handler(self, client):
        """Test custom 503 Service Unavailable exception handling."""
        # Add a temporary route to test ServiceUnavailableException
        @app.get("/api/test-503-endpoint")
        def route_raising_503():
            raise ServiceUnavailableException(detail="Cosmos DB cluster failover in progress.")

        response = client.get("/api/test-503-endpoint")
        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "Service Unavailable"
        assert data["status_code"] == 503
        assert "Cosmos DB cluster" in data["detail"]

    def test_dlq_and_quarantine_endpoints(self, client):
        """Test Dead Letter Queue & Quarantine API lifecycle."""
        # Check listing DLQ
        res_dlq = client.get("/api/dlq")
        assert res_dlq.status_code == 200
        assert isinstance(res_dlq.json(), list)

        # Check listing Quarantine
        res_qrn = client.get("/api/quarantine")
        assert res_qrn.status_code == 200
        assert isinstance(res_qrn.json(), list)
