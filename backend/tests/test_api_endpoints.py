from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_api_process_email_endpoint():
    payload = {
        "id": "EML-API-001",
        "sender": "ops@clearstream.com",
        "subject": "SWIFT MT564 - SAP SE Dividend EUR 2.20 per share - Ex 2024-05-18",
        "body": "Cash dividend distribution for ISIN DE0007164600 payable on 2024-05-25.",
        "received_at": "2024-05-10T10:00:00Z"
    }

    # Pass an incoming W3C traceparent header to test distributed propagation
    inbound_traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    response = client.post(
        "/api/process-email",
        json=payload,
        headers={"traceparent": inbound_traceparent}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email_id"] == "EML-API-001"
    assert "risk_score" in data
    assert "steps" in data

    # Verify W3C response headers
    assert "traceparent" in response.headers
    assert "X-Trace-ID" in response.headers
    assert response.headers["traceparent"].startswith("00-")


def test_api_stats_and_actions():
    response = client.get("/api/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_processed" in stats
    assert "auto_executed" in stats

    actions_resp = client.get("/api/actions")
    assert actions_resp.status_code == 200
    assert isinstance(actions_resp.json(), list)


def test_api_approval_flow():
    trace_id = "test-trace-id-12345"
    approve_resp = client.post(f"/api/approve/{trace_id}")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    reject_resp = client.post(f"/api/reject/{trace_id}")
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"
