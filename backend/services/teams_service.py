import logging
import json
from typing import Dict, Any, Optional
import httpx
from backend.config import TEAMS_WEBHOOK_URL

logger = logging.getLogger("mailmind.teams")


class TeamsService:
    """
    Microsoft Teams & HITL (Human-In-The-Loop) Alerting Service.
    Dispatches rich Adaptive Cards to Microsoft Teams channels for high-risk operations approvals,
    real-time escalation alerts, and critical SLA breach warnings.
    """

    def __init__(self):
        self.webhook_url = TEAMS_WEBHOOK_URL

    def generate_adaptive_card(self, pipeline_result: Any, email_subject: str = "", sender: str = "") -> Dict[str, Any]:
        """
        Builds a rich Adaptive Card v1.5 payload for Microsoft Teams.
        """
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
        """Sends an adaptive card to the configured Teams webhook."""
        card = self.generate_adaptive_card(pipeline_result, email_subject, sender)
        email_id = getattr(pipeline_result, "email_id", "unknown")
        logger.info("Generated MS Teams Adaptive Card for email %s (Risk: %.2f)", email_id, getattr(pipeline_result, 'risk_score', 0.0))

        if not self.webhook_url or "mock" in self.webhook_url:
            logger.info("MS Teams Webhook URL not live/mocked — Card logged successfully for HITL.")
            return True

        try:
            resp = httpx.post(self.webhook_url, json=card, timeout=5.0)
            return resp.status_code in [200, 202]
        except Exception as e:
            logger.warning("Could not dispatch live Teams card: %s", e)
            return False

    def send_notification(self, message: str, level: str = "INFO") -> bool:
        """Sends a text alert to the operations channel."""
        logger.info("Teams Notification [%s]: %s", level, message)
        if not self.webhook_url or "mock" in self.webhook_url:
            return True

        try:
            payload = {"text": f"[{level}] **MailMind Alert**: {message}"}
            resp = httpx.post(self.webhook_url, json=payload, timeout=5.0)
            return resp.status_code in [200, 202]
        except Exception as e:
            logger.warning("Could not send Teams notification: %s", e)
            return False
