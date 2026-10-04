import uuid
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

from backend.models.email_models import IncomingEmail, ClassifiedEmail, ExtractedEntities
from backend.models.agent_models import AgentStep, PipelineResult, AuditRecord
from backend.services.openai_service import OpenAIService
from backend.services.search_service import SearchService
from backend.services.cosmos_service import CosmosService
from backend.services.teams_service import TeamsService
from backend.services.pii_guardrail_service import PIIGuardrailService
from backend.agents.classifier import ClassifierAgent
from backend.agents.parser_agent import ParserAgent
from backend.agents.decision_agent import DecisionAgent
from backend.agents.risk_scorer import RiskScorerAgent
from backend.agents.action_executor import ActionExecutorAgent
from backend.config import RISK_THRESHOLD

logger = logging.getLogger("mailmind.orchestrator")


class MailMindOrchestrator:
    """
    Multi-Agent Financial Operations Orchestrator.
    Coordinates:
      1. PII & Security Guardrails Shield (Data Anonymization + Prompt Injection Defense)
      2. Classifier Agent (Capital Markets Intent Classification via GPT-4o)
      3. Parser Agent (Entity & Reference Data Extraction)
      4. Decision Agent (SOP & Institutional Memory Retrieval via Azure AI Search)
      5. Risk Scorer Agent (Operational Risk Assessment & Escalation Gating)
      6. Action Executor / HITL Gateway (Azure Functions Execution or MS Teams HITL Card)
      7. Cosmos DB Audit Trail & Compliance Recording
    """

    def __init__(self):
        self.openai = OpenAIService()
        self.search = SearchService()
        self.cosmos = CosmosService()
        self.teams = TeamsService()
        self.guardrail = PIIGuardrailService(masking_enabled=True, injection_shield_enabled=True)

        self.classifier = ClassifierAgent(self.openai)
        self.parser = ParserAgent(self.openai, self.search)
        self.decision = DecisionAgent(self.openai, self.search)
        self.risk_scorer = RiskScorerAgent(self.openai)
        self.executor = ActionExecutorAgent()

    def process_email(self, email: IncomingEmail) -> PipelineResult:
        steps: List[AgentStep] = []
        trace_id = str(uuid.uuid4())
        start_overall = time.time()

        # ── Step 0: PII Guardrails & Prompt Injection Defense ───────────────
        guard_start = time.time()
        raw_combined = f"{email.subject}\n{email.body}"
        sanitized_text, guardrail_report = self.guardrail.sanitize_and_guard(raw_combined)
        guard_dur = int((time.time() - guard_start) * 1000)

        # Create a sanitized copy of the email for LLM analysis
        sanitized_email = IncomingEmail(
            id=email.id,
            sender=email.sender,
            subject=email.subject,
            body=sanitized_text,
            received_at=email.received_at,
            attachments=email.attachments,
            raw_headers=email.raw_headers,
        )

        steps.append(
            AgentStep(
                agent_name="PIIGuardrailShield",
                input_data={"raw_length": guardrail_report.get("original_length")},
                output_data={
                    "pii_detected": guardrail_report.get("pii_detected"),
                    "masked_count": guardrail_report.get("mask_count"),
                    "masked_types": guardrail_report.get("masked_types"),
                    "injection_shield_passed": not guardrail_report.get("injection_flag"),
                },
                started_at=datetime.utcnow().isoformat(),
                completed_at=datetime.utcnow().isoformat(),
                duration_ms=guard_dur,
            )
        )

        # ── Step 1: Classification Agent ────────────────────────────────────
        c_start = datetime.utcnow().isoformat()
        classified, c_dur = self.classifier.run(sanitized_email)
        steps.append(
            AgentStep(
                agent_name="ClassifierAgent",
                input_data={"subject": sanitized_email.subject},
                output_data={
                    "intent": classified.intent.value,
                    "confidence": classified.confidence,
                    "urgency": classified.urgency.value,
                },
                started_at=c_start,
                completed_at=datetime.utcnow().isoformat(),
                duration_ms=c_dur,
            )
        )

        # ── Step 2: Parser & Reference Data Enrichment Agent ─────────────────
        p_start = datetime.utcnow().isoformat()
        masked_entities, p_dur = self.parser.run(classified)

        # De-mask entities back to real operational values for internal system calls
        real_entities_dict = self.guardrail.demask_entities(
            masked_entities.model_dump(), guardrail_report.get("mapping", {})
        )
        entities = ExtractedEntities(**real_entities_dict)

        # Enrich with Reference Data
        ref_data = {}
        if entities.isin:
            ref_data = self.search.search_reference_data(entities.isin)
        elif entities.cusip:
            ref_data = self.search.search_reference_data(entities.cusip)

        steps.append(
            AgentStep(
                agent_name="ParserAgent",
                input_data={"intent": classified.intent.value},
                output_data={
                    "entities": entities.model_dump(),
                    "reference_lookup": ref_data,
                },
                started_at=p_start,
                completed_at=datetime.utcnow().isoformat(),
                duration_ms=p_dur,
            )
        )

        # ── Step 3: Decision & SOP Retrieval Agent ───────────────────────────
        d_start = datetime.utcnow().isoformat()
        actions, d_dur = self.decision.run(classified, entities)
        retrieved_sops = self.search.search_sops(classified.intent.value)

        steps.append(
            AgentStep(
                agent_name="DecisionAgent",
                input_data={"entities_count": len(entities.model_dump(exclude_none=True))},
                output_data={
                    "action_count": len(actions),
                    "applied_sop": retrieved_sops[0]["id"] if retrieved_sops else "SOP-GEN-001",
                    "actions": [a.model_dump() for a in actions],
                },
                started_at=d_start,
                completed_at=datetime.utcnow().isoformat(),
                duration_ms=d_dur,
            )
        )

        # ── Step 4: Risk Scorer Agent ─────────────────────────────────────────
        r_start = datetime.utcnow().isoformat()
        risk_score, risk_level, r_dur = self.risk_scorer.run(classified, entities, actions)

        # Elevate risk if prompt injection attempt was flagged
        if guardrail_report.get("injection_flag"):
            risk_score = 1.0
            risk_level = "CRITICAL_INJECTION"

        anomaly_info = {}
        if hasattr(self.risk_scorer, "last_anomaly_result") and self.risk_scorer.last_anomaly_result:
            res = self.risk_scorer.last_anomaly_result
            anomaly_info = {
                "anomaly_score": res.anomaly_score,
                "risk_tags": res.risk_tags,
                "dimension_scores": res.dimension_scores,
                "recommendation": res.recommendation,
                "explanations": res.explanations,
            }

        steps.append(
            AgentStep(
                agent_name="RiskScorerAgent",
                input_data={"urgency": classified.urgency.value, "amount": entities.amount},
                output_data={
                    "risk_score": round(risk_score, 3),
                    "risk_level": risk_level,
                    "threshold": RISK_THRESHOLD,
                    "anomaly_shield": anomaly_info,
                },
                started_at=r_start,
                completed_at=datetime.utcnow().isoformat(),
                duration_ms=r_dur,
            )
        )

        # ── Step 5: Decision Gateway & Action Execution / HITL ───────────────
        requires_approval = risk_score >= RISK_THRESHOLD

        pipeline_result = PipelineResult(
            email_id=email.id,
            steps=steps,
            risk_score=round(risk_score, 3),
            risk_level=risk_level,
            recommended_actions=actions,
            requires_approval=requires_approval,
        )

        action_results = []
        if not requires_approval:
            for act in actions:
                res, dur = self.executor.run(act)
                action_results.append(res.model_dump())
                self.cosmos.save_action(res.model_dump())
            logger.info("Auto-executed %d actions for email %s", len(actions), email.id)
        else:
            # High-Risk Path: Trigger Microsoft Teams Adaptive Card & Supervisor Alert
            self.teams.send_approval_card(pipeline_result, email.subject, email.sender)
            logger.warning(
                "⚠️ High-risk action required approval for email %s (Risk: %.2f) — Teams Card dispatched.",
                email.id,
                risk_score,
            )

        # ── Step 6: Regulatory Audit Trail & Persistence ─────────────────────
        audit = AuditRecord(
            trace_id=trace_id,
            email_id=email.id,
            pipeline_result=pipeline_result,
            action_taken="AUTO_EXECUTED" if not requires_approval else "PENDING_SUPERVISOR_APPROVAL",
            action_result=action_results,
            created_at=datetime.utcnow().isoformat(),
        )

        self.cosmos.save_audit_trail(audit.model_dump())
        self.cosmos.save_email(email.model_dump())
        self.search.index_email(email.model_dump())

        total_ms = int((time.time() - start_overall) * 1000)
        logger.info("Pipeline completed in %d ms for %s", total_ms, email.id)

        return pipeline_result
