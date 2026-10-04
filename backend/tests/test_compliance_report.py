import re
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.compliance_report_generator import ComplianceReportGenerator


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def compliance_generator():
    return ComplianceReportGenerator()


def test_compliance_certificate_generation_structure(compliance_generator):
    """Test full certificate payload generation and regulatory fields."""
    email_data = {
        "id": "email_test_01",
        "sender": "settlements@euroclear.com",
        "subject": "Corporate Action Cash Distribution EUR 5,000,000",
        "body": "Mandatory Cash Dividend on ISIN FR0000120271. Credit Beneficiary IBAN FR7630006000011234567890189.",
        "received_at": "2026-10-04T12:00:00.000000Z",
    }
    
    pipeline_result = {
        "email_id": "email_test_01",
        "risk_score": 0.22,
        "risk_level": "LOW",
        "requires_approval": False,
        "steps": [
            {
                "agent_name": "PIIGuardrailShield",
                "started_at": "2026-10-04T12:00:00.100000Z",
                "completed_at": "2026-10-04T12:00:00.115000Z",
                "duration_ms": 15,
                "input_data": {"raw_length": 150},
                "output_data": {
                    "pii_detected": True,
                    "masked_count": 1,
                    "masked_types": ["IBAN"],
                    "injection_shield_passed": True,
                },
            },
            {
                "agent_name": "ClassifierAgent",
                "started_at": "2026-10-04T12:00:00.116000Z",
                "completed_at": "2026-10-04T12:00:00.320000Z",
                "duration_ms": 204,
                "input_data": {"subject": "Corporate Action Cash Distribution"},
                "output_data": {"intent": "CORPORATE_ACTION", "confidence": 0.99, "urgency": "MEDIUM"},
            },
            {
                "agent_name": "RiskScorerAgent",
                "started_at": "2026-10-04T12:00:00.321000Z",
                "completed_at": "2026-10-04T12:00:00.370000Z",
                "duration_ms": 49,
                "input_data": {"urgency": "MEDIUM"},
                "output_data": {"risk_score": 0.22, "risk_level": "LOW", "threshold": 0.70},
            },
        ],
        "recommended_actions": [
            {
                "action_type": "DIVIDEND_CLAIM_BOOK",
                "target_system": "TARGET2_GATEWAY",
                "parameters": {"isin": "FR0000120271", "amount": 5000000.0},
            }
        ],
    }

    cert = compliance_generator.generate_certificate_data(
        email_id="email_test_01",
        email_data=email_data,
        pipeline_result=pipeline_result,
    )

    # 1. MiFID II RTS 25 Clock Synchronization validation
    mifid = cert["mifid_ii_rts25"]
    assert "MiFID II RTS 25" in mifid["regulation"]
    assert mifid["clock_synchronization_status"] == "SYNCHRONIZED_ACCREDITED"
    # Verify microsecond precision ISO format: YYYY-MM-DDTHH:MM:SS.ffffffZ
    microsec_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
    assert re.match(microsec_pattern, mifid["timestamp_utc_microsecond"]) is not None
    assert mifid["audit_epoch_nanoseconds"] > 0

    # 2. FINRA Rule 4511 Record Retention validation
    finra = cert["finra_rule_4511"]
    assert "FINRA Rule 4511" in finra["mandate"]
    assert finra["retention_period_years"] == 6
    assert "WORM" in finra["storage_class"]
    assert re.match(microsec_pattern, finra["mandatory_retention_until_utc"]) is not None
    assert "Société Générale" in finra["custodian_entity"]

    # 3. PII Anonymization Proof validation
    pii = cert["pii_anonymization_proof"]
    assert "ZERO UNMASKED PII" in pii["attestation"]
    assert pii["certification_status"] == "PASSED_VERIFIED"
    assert len(pii["raw_payload_sha256"]) == 64
    assert len(pii["sanitized_payload_sha256"]) == 64
    assert pii["masked_entities_count"] == 1
    assert "IBAN" in pii["masked_entity_categories"]
    assert "ISIN" in pii["protected_market_identifiers"]
    assert "PASSED" in pii["prompt_injection_defense"]

    # 4. Multi-Agent Step Trace Lineage DAG validation
    dag = cert["multi_agent_lineage_dag"]
    assert dag["total_steps"] == 3
    assert len(dag["nodes"]) == 3
    assert len(dag["edges"]) == 2
    assert dag["nodes"][0]["agent_name"] == "PIIGuardrailShield"
    assert dag["nodes"][1]["agent_name"] == "ClassifierAgent"
    assert dag["nodes"][2]["agent_name"] == "RiskScorerAgent"
    assert dag["edges"][0]["from"] == dag["nodes"][0]["node_id"]
    assert dag["edges"][0]["to"] == dag["nodes"][1]["node_id"]

    # 5. Supervisor Cryptographic Approval Signature validation
    sig = cert["supervisor_signature"]
    assert sig["signing_algorithm"] == "HMAC-SHA256 (FIPS PUB 198-1)"
    assert len(sig["signature_hash"]) == 64
    assert sig["verification_status"] == "CRYPTOGRAPHICALLY_VERIFIED"
    assert cert["certificate_id"].startswith("CERT-SG-")


def test_cryptographic_signature_verification_and_tamper_detection(compliance_generator):
    """Test cryptographic verification succeeds for genuine certificates and fails on tampering."""
    cert = compliance_generator.generate_certificate_data(email_id="email_tamper_test")
    
    # Genuine certificate verification
    assert compliance_generator.verify_certificate(cert) is True

    # Tampered certificate (altering risk score)
    tampered_cert = dict(cert)
    tampered_cert["pipeline_execution_summary"] = dict(cert["pipeline_execution_summary"])
    tampered_cert["pipeline_execution_summary"]["risk_score"] = 0.99
    assert compliance_generator.verify_certificate(tampered_cert) is False

    # Tampered certificate (altering signature)
    tampered_sig_cert = dict(cert)
    tampered_sig_cert["supervisor_signature"] = dict(cert["supervisor_signature"])
    tampered_sig_cert["supervisor_signature"]["signature_hash"] = "0" * 64
    assert compliance_generator.verify_certificate(tampered_sig_cert) is False


def test_compliance_certificate_html_generation(compliance_generator):
    """Test PDF-printable HTML generation contains all required regulatory sections."""
    cert = compliance_generator.generate_certificate_data(email_id="email_html_test")
    html = compliance_generator.generate_certificate_html(cert)

    assert "<!DOCTYPE html>" in html
    assert "SOCIÉTÉ GÉNÉRALE GLOBAL BANKING" in html
    assert "MiFID II RTS 25" in html
    assert "FINRA Rule 4511" in html
    assert "ZERO UNMASKED PII TRANSMITTED" in html
    assert "Multi-Agent Execution Lineage DAG" in html
    assert "Cryptographic Supervisor Signature" in html
    assert "@media print" in html
    assert cert["certificate_id"] in html
    assert cert["supervisor_signature"]["signature_hash"] in html


def test_fastapi_compliance_certificate_json_endpoint(client):
    """Test /api/compliance/certificate/{email_id} returning JSON certificate."""
    response = client.get("/api/compliance/certificate/email_1?format=json")
    assert response.status_code == 200
    data = response.json()

    assert data["email_id"] == "email_1"
    assert "certificate_id" in data
    assert "mifid_ii_rts25" in data
    assert "finra_rule_4511" in data
    assert "pii_anonymization_proof" in data
    assert "multi_agent_lineage_dag" in data
    assert "supervisor_signature" in data
    assert data["mifid_ii_rts25"]["clock_synchronization_status"] == "SYNCHRONIZED_ACCREDITED"


def test_fastapi_compliance_certificate_html_endpoint(client):
    """Test /api/compliance/certificate/{email_id} returning printable HTML certificate."""
    response = client.get("/api/compliance/certificate/email_2?format=html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html_body = response.text

    assert "<!DOCTYPE html>" in html_body
    assert "SOCIÉTÉ GÉNÉRALE" in html_body
    assert "MiFID II RTS 25" in html_body
    assert "FINRA Rule 4511" in html_body
    assert "email_2" in html_body
