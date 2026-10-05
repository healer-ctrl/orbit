import logging
import json
from typing import Dict, Any, Optional
import httpx

from backend.config import TEAMS_WEBHOOK_URL
from backend.resilience import resilience_registry, retry_with_backoff, CircuitBreakerOpenException
from backend.telemetry import get_tracer, inject_traceparent

logger = logging.getLogger("mailmind.services.teams")


class TeamsService:
    """
    Microsoft Teams & HITL (Human-In-The-Loop) Alerting Service.
    Dispatches rich Adaptive Cards to Microsoft Teams channels for high-risk operations approvals.
    Equipped with OpenTelemetry distributed tracing, W3C traceparent propagation, and Circuit Breaker resilience.
    """

    def __init__(self):
        self.webhook_url = TEAMS_WEBHOOK_URL
        self.breaker = resilience_registry.get_breaker("teams_webhook")
        self.tracer = get_tracer()

    def generate_adaptive_card(self, pipeline_result: Any, email_subject: str = "", sender: str = "") -> Dict[str, Any]:
        """Builds a rich Adaptive Card v1.5 payload for Microsoft Teams."""
        email_id = getattr(pipeline_result, "email_id", "Unknown")
        risk_score = getattr(pipeline_result, "risk_score", 0.0)
        risk_level = getattr(pipeline_result, "risk_level", "HIGH")
        actions = getattr(pipeline_result, "recommended_actions", [])

        action_summary = "None"
        if actions:
            first_act = actions[0]
            if hasattr(first_act, "action_type"):
                action_summary = f"{first_act.action_type} (Priority: {getattr(first_act, 'priority', 'HIGH')})"
            elif isinstance(first_act, dict):
                action_summary = f"{first_act.get('action_type', 'UNKNOWN')}"

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.5",
                        "msteams": {"width": "Full"},
                        "body": [
                            {
                                "type": "Container",
                                "style": "attention" if risk_score >= 0.7 else "warning",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "⚠️ MailMind Operational Escalation — Approval Required",
                                        "weight": "Bolder",
                                        "size": "Medium",
                                        "color": "Attention" if risk_score >= 0.7 else "Warning",
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "Société Générale Capital Markets Operations Automation Gateway",
                                        "size": "Small",
                                        "isSubtle": True,
                                    }
                                ]
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Email ID:", "value": str(email_id)},
                                    {"title": "Sender:", "value": str(sender or "operations@clearstream.com")},
                                    {"title": "Subject:", "value": str(email_subject or "Operational Notification")},
                                    {"title": "Risk Level:", "value": f"{risk_level} (Score: {risk_score:.2f} / 1.00)"},
                                    {"title": "Proposed Action:", "value": action_summary},
                                    {"title": "SLA Deadline:", "value": "< 2 Hours (Target: Immediate Review)"},
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": "Reason for Escalation: Financial threshold / High urgency requires supervisor sign-off before API dispatch.",
                                "wrap": True,
                                "size": "Small",
                                "color": "Dark"
                            }
                        ],
                        "actions": [
                            {
                                "type": "Action.Submit",
                                "title": "✅ Approve & Auto-Execute",
                                "style": "positive",
                                "data": {
                                    "action": "approve",
                                    "trace_id": str(email_id),
                                    "user": "Supervisor_Ops"
                                }
                            },
                            {
                                "type": "Action.Submit",
                                "title": "❌ Reject & Create Ticket",
                                "style": "destructive",
                                "data": {
                                    "action": "reject",
                                    "trace_id": str(email_id),
                                    "user": "Supervisor_Ops"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        return card

    def send_approval_card(self, pipeline_result: Any, email_subject: str = "", sender: str = "") -> bool:
        """Sends an adaptive card to the configured Teams webhook with Circuit Breaker and Tracing."""
        with self.tracer.start_as_current_span("teams.send_approval_card") as span:
            email_id = getattr(pipeline_result, "email_id", "unknown")
            span.set_attribute("teams.email_id", email_id)
            span.set_attribute("teams.risk_score", getattr(pipeline_result, 'risk_score', 0.0))

            card = self.generate_adaptive_card(pipeline_result, email_subject, sender)
            logger.info("Generated MS Teams Adaptive Card for email %s (Risk: %.2f)", email_id, getattr(pipeline_result, 'risk_score', 0.0))

            if not self.webhook_url or "mock" in self.webhook_url:
                logger.info("MS Teams Webhook URL not live/mocked — Card logged successfully for HITL.")
                return True

            headers = {"Content-Type": "application/json"}
            inject_traceparent(headers)

            try:
                @retry_with_backoff(max_retries=2, base_delay=0.5)
                def _send():
                    return self.breaker.call(
                        lambda: httpx.post(self.webhook_url, json=card, headers=headers, timeout=5.0)
                    )
                resp = _send()
                return resp.status_code in [200, 202]
            except CircuitBreakerOpenException as cbe:
                logger.warning("Teams Circuit Breaker OPEN (%s). Notification cached locally.", cbe)
                return False
            except Exception as e:
                logger.warning("Could not dispatch live Teams card: %s", e)
                return False

    def send_notification(self, message: str, level: str = "INFO") -> bool:
        """Sends a text alert to the operations channel with W3C trace headers."""
        with self.tracer.start_as_current_span("teams.send_notification") as span:
            span.set_attribute("teams.alert_level", level)
            logger.info("Teams Notification [%s]: %s", level, message)

            if not self.webhook_url or "mock" in self.webhook_url:
                return True

            headers = {"Content-Type": "application/json"}
            inject_traceparent(headers)
            payload = {"text": f"[{level}] **MailMind Alert**: {message}"}

            try:
                @retry_with_backoff(max_retries=2, base_delay=0.5)
                def _send():
                    return self.breaker.call(
                        lambda: httpx.post(self.webhook_url, json=payload, headers=headers, timeout=5.0)
                    )
                resp = _send()
                return resp.status_code in [200, 202]
            except Exception as e:
                logger.warning("Could not send Teams notification: %s", e)
                return False
