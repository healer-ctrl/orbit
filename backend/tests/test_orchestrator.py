import pytest
from backend.models.email_models import IncomingEmail, Intent, Urgency
from backend.models.agent_models import PipelineResult
from backend.agents.orchestrator import MailMindOrchestrator
from backend.services.dlq_service import DLQStatus, QuarantineStatus


class TestOrchestratorPipeline:
    """Test suite for the MailMind multi-agent orchestration pipeline."""

    def test_pipeline_corporate_action_low_risk_auto_executes(self, orchestrator, corporate_action_email):
        """Test low-risk corporate action email goes through full pipeline and auto-executes."""
        result = orchestrator.process_email(corporate_action_email)

        assert isinstance(result, PipelineResult)
        assert result.email_id == corporate_action_email.id
        assert len(result.steps) >= 5

        # Check step sequence
        step_names = [s.agent_name for s in result.steps]
        assert "PIIGuardrailShield" in step_names
        assert "ClassifierAgent" in step_names
        assert "ParserAgent" in step_names
        assert "DecisionAgent" in step_names
        assert "RiskScorerAgent" in step_names

        # Verify low risk (< 0.7) and auto-execution
        assert result.risk_score < 0.7
        assert result.requires_approval is False
        assert len(result.recommended_actions) > 0
        assert result.recommended_actions[0].action_type == "CORPORATE_ACTION"

    def test_pipeline_high_risk_settlement_escalates_to_hitl(self, orchestrator, high_risk_settlement_email):
        """Test high-risk settlement failure (> $2M, urgent) requires supervisor approval."""
        result = orchestrator.process_email(high_risk_settlement_email)

        assert isinstance(result, PipelineResult)
        assert result.risk_score >= 0.7
        assert result.requires_approval is True
        assert len(result.recommended_actions) > 0

        # Check classification
        classifier_step = next(s for s in result.steps if s.agent_name == "ClassifierAgent")
        assert classifier_step.output_data["intent"] == "SETTLEMENT"
        assert classifier_step.output_data["urgency"] == "HIGH"

    def test_pipeline_trade_linkage_intent(self, orchestrator):
        """Test trade linkage intent processing."""
        email = IncomingEmail(
            id="test_tl_01",
            sender="trader@socgen.com",
            subject="Please link trade TRD-2024-88712 to CUSIP 037833100",
            body="Please allocate and link block trade TRD-2024-88712 to Apple Inc (CUSIP: 037833100, ISIN: US0378331005).",
            received_at="2024-05-12T11:00:00Z",
        )
        result = orchestrator.process_email(email)

        assert isinstance(result, PipelineResult)
        classifier_step = next(s for s in result.steps if s.agent_name == "ClassifierAgent")
        assert classifier_step.output_data["intent"] == "TRADE_LINKAGE"

        parser_step = next(s for s in result.steps if s.agent_name == "ParserAgent")
        entities = parser_step.output_data["entities"]
        assert entities.get("cusip") == "037833100"
        assert entities.get("trade_id") == "TRD-2024-88712"

    def test_pipeline_instrument_correction_intent(self, orchestrator):
        """Test instrument correction intent processing."""
        email = IncomingEmail(
            id="test_ic_01",
            sender="data-quality@socgen.com",
            subject="ALERT: Security Identifier Mismatch Detected for POS-44332",
            body="Position POS-44332 currently mapped to obsolete ISIN XS1234567890. Please update instrument master mapping.",
            received_at="2024-05-13T08:00:00Z",
        )
        result = orchestrator.process_email(email)
        classifier_step = next(s for s in result.steps if s.agent_name == "ClassifierAgent")
        assert classifier_step.output_data["intent"] == "INSTRUMENT_CORRECTION"

    def test_pipeline_support_ticket_intent(self, orchestrator):
        """Test support ticket intent processing."""
        email = IncomingEmail(
            id="test_sup_01",
            sender="user@socgen.com",
            subject="Access Provisioning Request: New Analyst Onboarding",
            body="Please provision Trade Booking & Settlement Portal access for John Doe.",
            received_at="2024-05-14T10:00:00Z",
        )
        result = orchestrator.process_email(email)
        classifier_step = next(s for s in result.steps if s.agent_name == "ClassifierAgent")
        assert classifier_step.output_data["intent"] == "SUPPORT_TICKET"

    def test_pipeline_error_routes_to_dlq_gracefully(self, orchestrator, monkeypatch):
        """Test unhandled exception in downstream agent triggers DLQ enqueue without crashing."""
        def mock_failing_classifier(email):
            raise RuntimeError("Database connection timed out during classification")

        monkeypatch.setattr(orchestrator.classifier, "run", mock_failing_classifier)

        email = IncomingEmail(
            id="test_fail_dlq",
            sender="fail@test.com",
            subject="Error trigger email",
            body="This email triggers an intentional mock failure.",
            received_at="2024-05-15T00:00:00Z",
        )

        result = orchestrator.process_email(email)

        assert isinstance(result, PipelineResult)
        assert result.risk_level == "EXECUTION_FAILED"
        assert result.requires_approval is True

        # Verify DLQ message was enqueued
        dlq_msgs = orchestrator.dlq.list_dlq_messages()
        matching = [m for m in dlq_msgs if m.email_id == "test_fail_dlq"]
        assert len(matching) == 1
        assert matching[0].error_type == "RuntimeError"
        assert "Database connection timed out" in matching[0].error_message

    def test_pipeline_all_sample_emails_processed(self, orchestrator, sample_emails):
        """Test batch processing of all repository sample emails."""
        for email_dict in sample_emails:
            email = IncomingEmail(**email_dict)
            result = orchestrator.process_email(email)
            assert isinstance(result, PipelineResult)
            assert result.email_id == email.id
            assert len(result.steps) >= 5
