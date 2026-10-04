from typing import Dict, Any
import time
import uuid
from datetime import datetime
from backend.models.action_models import ActionRequest, ActionResult, ActionStatus


class TradeLinkageHandler:
    """Simulates linking trades to instruments in a booking system."""

    def execute(self, request: ActionRequest) -> ActionResult:
        time.sleep(0.6)

        payload = request.payload or {}

        return ActionResult(
            action_id=f"TL-{request.trace_id[:8]}",
            action_type=request.action_type,
            status=ActionStatus.SUCCESS,
            result_data={
                "linkage_id": f"LNK-{uuid.uuid4().hex[:8].upper()}",
                "trade_id": payload.get("trade_id", "TRD-2024-88712"),
                "instrument": {
                    "cusip": payload.get("cusip", "037833100"),
                    "isin": payload.get("isin", "US0378331005"),
                    "name": payload.get("instrument_name", "Apple Inc."),
                    "type": "EQUITY",
                    "exchange": "NASDAQ",
                },
                "booking_details": {
                    "book": "EQ-US-FLOW",
                    "desk": "US Equities Trading",
                    "trader": "desk_head_us_eq",
                },
                "amount": payload.get("amount", 1_500_000),
                "currency": payload.get("currency", "USD"),
                "linkage_status": "LINKED",
                "previous_linkage": None,
                "audit_note": "Trade linked by MailMind AI agent",
                "processed_at": datetime.utcnow().isoformat(),
            },
            executed_at=datetime.utcnow().isoformat(),
        )
