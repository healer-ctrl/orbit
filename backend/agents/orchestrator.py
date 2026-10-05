import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.models.email_models import IncomingEmail, ClassifiedEmail, ExtractedEntities
from backend.models.agent_models import AgentStep, PipelineResult, AuditRecord
from backend.services.openai_service import OpenAIService
from backend.services.search_service import SearchService
from backend.services.cosmos_service import CosmosService
from backend.services.teams_service import TeamsService
from backend.services.pii_guardrail_service import PIIGuardrailService
from backend.services.dlq_service import DeadLetterQueueService, ThreatLevel, QuarantineStatus
from backend.agents.classifier import ClassifierAgent
from backend.agents.parser_agent import ParserAgent
from backend.agents.decision_agent import DecisionAgent
from backend.agents.risk_scorer import RiskScorerAgent
from backend.agents.action_executor import ActionExecutorAgent
from backend.config import RISK_THRESHOLD
from backend.telemetry import (
    get_tracer,
    get_current_trace_id,
    get_current_span_id,
    get_current_traceparent,
    trace_agent_step,
)

logger = logging.getLogger("mailmind.agents.orchestrator")


class MailMindOrchestrator:
    """
    Multi-Agent Financial Operations Orchestrator.
    Equipped with OpenTelemetry distributed tracing and W3C traceparent propagation
    across all multi-agent steps.
    """

    def __init__(self):
        self.openai = OpenAIService()
        self.search = SearchService()
        self.cosmos = CosmosService()
        self.teams = TeamsService()
        self.guardrail = PIIGuardrailService(masking_enabled=True, injection_shield_enabled=True)
        self.dlq = DeadLetterQueueService(cosmos_service=self.cosmos)

        self.classifier = ClassifierAgent(self.openai)
        self.parser = ParserAgent(self.openai, self.search)
        self.decision = DecisionAgent(self.openai, self.search)
        self.risk_scorer = RiskScorerAgent(self.openai)
        self.executor = ActionExecutorAgent()
        self.tracer = get_tracer()

    def process_email(self, email: IncomingEmail, parent_traceparent: Optional[str] = None) -> PipelineResult:
        """
        Executes the multi-agent pipeline with end-to-end W3C traceparent propagation.
        """
        with self.tracer.start_as_current_span("orchestrator.process_email") as root_span:
            root_span.set_attribute("email.id", email.id)
            root_span.set_attribute("email.sender", email.sender)
            root_span.set_attribute("email.subject", email.subject)

            trace_id = get_current_trace_id()
            if trace_id == "0" * 32:
                trace_id = uuid.uuid4().hex
            pipeline_traceparent = get_current_traceparent()

            steps: List[AgentStep] = []
            start_overall = time.time()

            try:
                # ── Step 0: PII Guardrails & Prompt Injection Defense ───────
                with trace_agent_step("PIIGuardrailShield", {"email_id": email.id}) as span:
                    guard_start = time.time()
                    raw_combined = f"{email.subject}\n{email.body}"
                    sanitized_text, guardrail_report = self.guardrail.sanitize_and_guard(raw_combined)
                    guard_dur = int((time.time() - guard_start) * 1000)

                    sanitized_email = IncomingEmail(
                        id=email.id,
                        sender=email.sender,
                        subject=email.subject,
                        body=sanitized_text,
                        received_at=email.received_at,
                        attachments=email.attachments,
                        raw_headers=email.raw_headers,
                    )

                    step_tp = get_current_traceparent()
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
                            started_at=datetime.now(timezone.utc).isoformat(),
                            completed_at=datetime.now(timezone.utc).isoformat(),
                            duration_ms=guard_dur,
                            trace_id=trace_id,
                            span_id=get_current_span_id(),
                            traceparent=step_tp,
                        )
                    )

                # Check if prompt injection is detected
                is_prompt_injection = bool(guardrail_report.get("injection_flag"))
                if is_prompt_injection:
                    self.dlq.quarantine_email(
                        email_id=email.id,
                        raw_payload=email.model_dump(),
                        reason="Prompt injection attempt detected",
                        threat_level=ThreatLevel.CRITICAL,
                        details=guardrail_report.get("injection_details", []),
                    )

                # ── Step 1: Classification Agent ────────────────────────────
                with trace_agent_step("ClassifierAgent", {"subject": sanitized_email.subject}) as span:
                    c_start_iso = datetime.now(timezone.utc).isoformat()
                    classified, c_dur = self.classifier.run(sanitized_email)
                    span.set_attribute("classified.intent", classified.intent.value)
                    span.set_attribute("classified.urgency", classified.urgency.value)

                    step_tp = get_current_traceparent()
                    steps.append(
                        AgentStep(
                            agent_name="ClassifierAgent",
                            input_data={"subject": sanitized_email.subject},
                            output_data={
                                "intent": classified.intent.value,
                                "confidence": classified.confidence,
                                "urgency": classified.urgency.value,
                            },
                            started_at=c_start_iso,
                            completed_at=datetime.now(timezone.utc).isoformat(),
                            duration_ms=c_dur,
                            trace_id=trace_id,
                            span_id=get_current_span_id(),
                            traceparent=step_tp,
                        )
                    )

                # ── Step 2: Parser & Reference Data Enrichment Agent ─────────
                with trace_agent_step("ParserAgent", {"intent": classified.intent.value}) as span:
                    p_start_iso = datetime.now(timezone.utc).isoformat()
                    masked_entities, p_dur = self.parser.run(classified)

                    # De-mask entities back to operational values for internal system calls
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

                    step_tp = get_current_traceparent()
                    steps.append(
                        AgentStep(
                            agent_name="ParserAgent",
                            input_data={"intent": classified.intent.value},
                            output_data={
                                "entities": entities.model_dump(),
                                "reference_lookup": ref_data,
                            },
                            started_at=p_start_iso,
                            completed_at=datetime.now(timezone.utc).isoformat(),
                            duration_ms=p_dur,
                            trace_id=trace_id,
                            span_id=get_current_span_id(),
                            traceparent=step_tp,
                        )
                    )

                # ── Step 3: Decision & SOP Retrieval Agent ───────────────────
                with trace_agent_step("DecisionAgent", {"intent": classified.intent.value}) as span:
                    d_start_iso = datetime.now(timezone.utc).isoformat()
                    actions, d_dur = self.decision.run(classified, entities)
                    retrieved_sops = self.search.search_sops(classified.intent.value)

                    # If prompt injection, block recommended actions
                    if is_prompt_injection:
                        actions = []

                    step_tp = get_current_traceparent()
                    steps.append(
                        AgentStep(
                            agent_name="DecisionAgent",
                            input_data={"entities_count": len(entities.model_dump(exclude_none=True))},
                            output_data={
                                "action_count": len(actions),
                                "applied_sop": retrieved_sops[0]["id"] if retrieved_sops else "SOP-GEN-001",
                                "actions": [a.model_dump() for a in actions],
                            },
                            started_at=d_start_iso,
                            completed_at=datetime.now(timezone.utc).isoformat(),
                            duration_ms=d_dur,
                            trace_id=trace_id,
                            span_id=get_current_span_id(),
                            traceparent=step_tp,
                        )
                    )

                # ── Step 4: Risk Scorer Agent ─────────────────────────────────
                with trace_agent_step("RiskScorerAgent", {"urgency": classified.urgency.value}) as span:
                    r_start_iso = datetime.now(timezone.utc).isoformat()
                    risk_score, risk_level, r_dur = self.risk_scorer.run(classified, entities, actions)

                    if is_prompt_injection:
                        risk_score = 1.0
                        risk_level = "CRITICAL_INJECTION"

                    span.set_attribute("risk.score", risk_score)
                    span.set_attribute("risk.level", risk_level)

                    step_tp = get_current_traceparent()
                    steps.append(
                        AgentStep(
                            agent_name="RiskScorerAgent",
                            input_data={"urgency": classified.urgency.value, "amount": entities.amount},
                            output_data={
                                "risk_score": round(risk_score, 3),
                                "risk_level": risk_level,
                                "threshold": RISK_THRESHOLD,
                            },
                            started_at=r_start_iso,
                            completed_at=datetime.now(timezone.utc).isoformat(),
                            duration_ms=r_dur,
                            trace_id=trace_id,
                            span_id=get_current_span_id(),
                            traceparent=step_tp,
                        )
                    )

                # ── Step 5: Decision Gateway & Action Execution / HITL ───────
                requires_approval = risk_score >= RISK_THRESHOLD

                pipeline_result = PipelineResult(
                    email_id=email.id,
                    trace_id=trace_id,
                    traceparent=pipeline_traceparent,
                    steps=steps,
                    risk_score=round(risk_score, 3),
                    risk_level=risk_level,
                    recommended_actions=actions,
                    requires_approval=requires_approval,
                )

                action_results = []
                if not requires_approval and actions:
                    with trace_agent_step("ActionExecutorAgent", {"actions_count": len(actions)}) as span:
                        for act in actions:
                            res, dur = self.executor.run(act)
                            action_results.append(res.model_dump())
                            self.cosmos.save_action(res.model_dump())
                        logger.info("Auto-executed %d actions for email %s", len(actions), email.id)
                elif requires_approval and not is_prompt_injection:
                    with trace_agent_step("TeamsHITLGateway", {"email_id": email.id}) as span:
                        self.teams.send_approval_card(pipeline_result, email.subject, email.sender)
                        logger.warning(
                            "⚠️ High-risk action required approval for email %s (Risk: %.2f) — Teams Card dispatched.",
                            email.id,
                            risk_score,
                        )

                # ── Step 6: Regulatory Audit Trail & Persistence ─────────────
                with trace_agent_step("AuditPersistence", {"trace_id": trace_id}) as span:
                    action_taken = "QUARANTINED_POISON_PAYLOAD" if is_prompt_injection else (
                        "AUTO_EXECUTED" if not requires_approval else "PENDING_SUPERVISOR_APPROVAL"
                    )
                    audit = AuditRecord(
                        trace_id=trace_id,
                        traceparent=pipeline_traceparent,
                        email_id=email.id,
                        pipeline_result=pipeline_result,
                        action_taken=action_taken,
                        action_result=action_results,
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )

                    self.cosmos.save_audit_trail(audit.model_dump())
                    self.cosmos.save_email(email.model_dump())
                    self.search.index_email(email.model_dump())

                total_ms = int((time.time() - start_overall) * 1000)
                root_span.set_attribute("pipeline.duration_ms", total_ms)
                root_span.set_attribute("pipeline.requires_approval", requires_approval)
                logger.info("Pipeline completed in %d ms for %s (TraceID: %s)", total_ms, email.id, trace_id)

                return pipeline_result

            except Exception as e:
                logger.error("Pipeline failed for email %s: %s", email.id, e, exc_info=True)
                self.dlq.enqueue_failed(
                    email_id=email.id,
                    payload=email.model_dump(),
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                return PipelineResult(
                    email_id=email.id,
                    trace_id=trace_id,
                    traceparent=pipeline_traceparent,
                    steps=steps,
                    risk_score=1.0,
                    risk_level="EXECUTION_FAILED",
                    recommended_actions=[],
                    requires_approval=True,
                )
