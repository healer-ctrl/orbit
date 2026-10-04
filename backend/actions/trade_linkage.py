from typing import Dict, Any
import time
import uuid
from datetime import datetime
from backend.models.action_models import ActionRequest, ActionResult, ActionStatus
from backend.services.swift_engine import SWIFTEngine


class TradeLinkageHandler:
    """Simulates linking trades to instruments in a booking system with SWIFT confirmation generation."""

    def __init__(self):
        self.swift_engine = SWIFTEngine()

    def execute(self, request: ActionRequest) -> ActionResult:
        time.sleep(0.4)

        payload = request.payload or {}
        trade_id = payload.get("trade_id", "TRD-2024-88712")
        isin = payload.get("isin", "US0378331005")
        instrument_name = payload.get("instrument_name", "Apple Inc.")
        amount = payload.get("amount", 1_500_000.0)
        currency = payload.get("currency", "USD")

        swift_mt544 = self.swift_engine.generate_mt544(
            trade_id=trade_id,
            isin=isin,
            instrument_name=instrument_name,
            amount=amount,
            currency=currency,
            safekeeping_account="EQ-US-FLOW",
            narrative="BLOCK TRADE ALLOCATION TO EQ-US-FLOW",
        )

        iso20022_pacs008 = self.swift_engine.generate_pacs_008(
            transaction_id=trade_id,
            amount=amount,
            currency=currency,
            remittance_info=f"Block Trade Linkage {trade_id} Apple Inc",
        )

        return ActionResult(
            action_id=f"TL-{request.trace_id[:8]}",
            action_type=request.action_type,
            status=ActionStatus.SUCCESS,
            result_data={
                "linkage_id": f"LNK-{uuid.uuid4().hex[:8].upper()}",
                "trade_id": trade_id,
                "instrument": {
                    "cusip": payload.get("cusip", "037833100"),
                    "isin": isin,
                    "name": instrument_name,
                    "type": "EQUITY",
                    "exchange": "NASDAQ",
                },
                "booking_details": {
                    "book": "EQ-US-FLOW",
                    "desk": "US Equities Trading",
                    "trader": "desk_head_us_eq",
                },
                "amount": amount,
                "currency": currency,
                "linkage_status": "LINKED",
                "previous_linkage": None,
                "audit_note": "Trade linked by MailMind AI agent",
                "swift_mt544": swift_mt544,
                "iso20022_pacs008": iso20022_pacs008,
                "processed_at": datetime.utcnow().isoformat(),
            },
            executed_at=datetime.utcnow().isoformat(),
        )
