import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.config import get_secret, TEAMS_WEBHOOK_URL
import httpx

logger = logging.getLogger("orbit.alerting")


class SystemAlert(BaseModel):
    id: str
    severity: str  # "INFO", "WARNING", "ERROR", "CRITICAL"
    category: str  # "SLA_BREACH", "CIRCUIT_BREAKER", "ERROR_SPIKE", "DLQ_THRESHOLD", "SECURITY_ANOMALY"
    title: str
    description: str
    component: str
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    trace_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved: bool = False


class AlertingService:
    """Enterprise SRE & Technical Alerting Engine for Orbit."""

    def __init__(self):
        self.alerts_history: List[SystemAlert] = []
        self._seed_initial_alerts()

    def _seed_initial_alerts(self):
        self.alerts_history = [
            SystemAlert(
                id="ALT-2026-1001",
                severity="WARNING",
                category="SLA_BREACH",
                title="P99 Latency SLA Warning (> 4000ms)",
                description="Cold start LLM fallback exceeded 3500ms budget during burst ingestion.",
                component="AzureOpenAI",
                metric_value=4340.0,
                threshold_value=2500.0,
                trace_id="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                resolved=True,
            ),
            SystemAlert(
                id="ALT-2026-1002",
                severity="INFO",
                category="CIRCUIT_BREAKER",
                title="Circuit Breaker Auto-Reset to CLOSED",
                description="Azure AI Search circuit breaker completed probe in HALF-OPEN state and recovered to CLOSED.",
                component="AzureAISearch",
                metric_value=0.0,
                threshold_value=0.0,
                trace_id="00-8a3c2e1f4b5d6a7e8f9a0b1c2d3e4f5a-11a2b3c4d5e6f7a8-01",
                resolved=True,
            ),
            SystemAlert(
                id="ALT-2026-1003",
                severity="CRITICAL",
                category="SECURITY_ANOMALY",
                title="Prompt Injection Attack Defended",
                description="Suspicious instruction override attempt detected and quarantined into DLQ.",
                component="PIIGuardrailShield",
                metric_value=1.0,
                threshold_value=0.7,
                trace_id="00-9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c-22b3c4d5e6f7a8b9-01",
                resolved=True,
            )
        ]

    def trigger_alert(
        self,
        severity: str,
        category: str,
        title: str,
        description: str,
        component: str,
        metric_value: Optional[float] = None,
        threshold_value: Optional[float] = None,
        trace_id: Optional[str] = None,
    ) -> SystemAlert:
        alert = SystemAlert(
            id=f"ALT-{int(time.time()*1000)%1000000:06d}",
            severity=severity,
            category=category,
            title=title,
            description=description,
            component=component,
            metric_value=metric_value,
            threshold_value=threshold_value,
            trace_id=trace_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            resolved=False,
        )
        self.alerts_history.insert(0, alert)
        logger.warning(
            "🚨 [ALERT %s][%s] %s: %s (Component: %s)",
            severity, category, title, description, component
        )

        # Dispatch alert webhook asynchronously or notify Teams
        self._dispatch_notification(alert)
        return alert

    def _dispatch_notification(self, alert: SystemAlert):
        """Sends alert notification to Microsoft Teams / Azure Monitor."""
        webhook_url = TEAMS_WEBHOOK_URL
        if not webhook_url or "mock-approval" in webhook_url:
            logger.info("Notification logged locally for alert %s", alert.id)
            return

        try:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "FF0000" if alert.severity == "CRITICAL" else "FFA500",
                "summary": f"Orbit SRE Alert: {alert.title}",
                "sections": [{
                    "activityTitle": f"🚨 Orbit SRE Alert — [{alert.severity}] {alert.category}",
                    "activitySubtitle": f"Component: {alert.component} | Time: {alert.created_at}",
                    "facts": [
                        {"name": "Alert ID", "value": alert.id},
                        {"name": "Title", "value": alert.title},
                        {"name": "Description", "value": alert.description},
                        {"name": "Metric Value", "value": str(alert.metric_value)},
                        {"name": "Threshold", "value": str(alert.threshold_value)},
                        {"name": "Trace ID", "value": alert.trace_id or "N/A"},
                    ],
                    "markdown": True,
                }]
            }
            httpx.post(webhook_url, json=payload, timeout=3.0)
        except Exception as e:
            logger.error("Failed to dispatch alert webhook: %s", e)

    def list_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [a.model_dump() for a in self.alerts_history[:limit]]


alerting_service = AlertingService()
