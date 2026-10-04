from typing import Dict, Any
import time
import uuid
from datetime import datetime, timedelta
from backend.models.action_models import ActionRequest, ActionResult, ActionStatus


class CorporateActionHandler:
    """Simulates corporate action event creation in a CA processing system."""

    def execute(self, request: ActionRequest) -> ActionResult:
        time.sleep(0.8)  # simulate API latency

        event_id = f"CA-EVT-{uuid.uuid4().hex[:8].upper()}"
        payload = request.payload or {}

        return ActionResult(
            action_id=f"CA-{request.trace_id[:8]}",
            action_type=request.action_type,
            status=ActionStatus.SUCCESS,
            result_data={
                "event_id": event_id,
                "event_type": payload.get("action_type", "CASH_DIVIDEND"),
                "isin": payload.get("isin", "DE0007164600"),
                "instrument_name": payload.get("instrument_name", "SAP SE"),
                "ex_date": payload.get("trade_date", "2024-05-18"),
                "record_date": "2024-05-19",
                "payment_date": "2024-05-22",
                "rate_per_share": payload.get("amount", 2.20),
                "currency": payload.get("currency", "EUR"),
                "affected_positions": 14,
                "total_entitlement": 30800.00,
                "status": "CREATED",
                "notification_sent": True,
                "swift_message": "MT566 generated",
                "processed_at": datetime.utcnow().isoformat(),
            },
            executed_at=datetime.utcnow().isoformat(),
        )
