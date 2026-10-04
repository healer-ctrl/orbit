from typing import Dict, Any
import time
import uuid
from datetime import datetime, timedelta
from backend.models.action_models import ActionRequest, ActionResult, ActionStatus
from backend.services.swift_engine import SWIFTEngine


class CorporateActionHandler:
    """Simulates corporate action event creation in a CA processing system with SWIFT ISO 15022/20022 generation."""

    def __init__(self):
        self.swift_engine = SWIFTEngine()

    def execute(self, request: ActionRequest) -> ActionResult:
        time.sleep(0.5)  # simulate API latency

        event_id = f"CA-EVT-{uuid.uuid4().hex[:8].upper()}"
        payload = request.payload or {}
        isin = payload.get("isin", "DE0007164600")
        instrument_name = payload.get("instrument_name", "SAP SE")
        rate = payload.get("amount", 2.20)
        currency = payload.get("currency", "EUR")
        ex_date = payload.get("trade_date", "2024-05-18")
        record_date = "2024-05-19"
        payment_date = "2024-05-22"

        # Generate standard SWIFT ISO 15022 MT564 and MT566
        swift_mt564 = self.swift_engine.generate_mt564(
            corporate_action_ref=event_id,
            isin=isin,
            instrument_name=instrument_name,
            event_type="DIVI",
            mandatory_flag="MAND",
            ex_date=ex_date,
            record_date=record_date,
            payment_date=payment_date,
            rate_per_share=rate,
            currency=currency,
            narrative="MANDATORY CASH DIVIDEND CREATED BY MAILMIND",
        )

        swift_mt566 = self.swift_engine.generate_mt566(
            corporate_action_ref=event_id,
            isin=isin,
            payment_date=payment_date,
            total_entitlement=30800.00,
            currency=currency,
        )

        # Generate standard ISO 20022 seev.031 XML
        iso20022_seev = self.swift_engine.generate_seev_031(
            corporate_action_ref=event_id,
            isin=isin,
            instrument_name=instrument_name,
            event_type="DVCA",
            ex_date=ex_date,
            record_date=record_date,
            payment_date=payment_date,
            rate_per_share=rate,
            currency=currency,
        )

        mt564_val = self.swift_engine.validate_swift_message(swift_mt564)

        return ActionResult(
            action_id=f"CA-{request.trace_id[:8]}",
            action_type=request.action_type,
            status=ActionStatus.SUCCESS,
            result_data={
                "event_id": event_id,
                "event_type": payload.get("action_type", "CASH_DIVIDEND"),
                "isin": isin,
                "instrument_name": instrument_name,
                "ex_date": ex_date,
                "record_date": record_date,
                "payment_date": payment_date,
                "rate_per_share": rate,
                "currency": currency,
                "affected_positions": 14,
                "total_entitlement": 30800.00,
                "status": "CREATED",
                "notification_sent": True,
                "swift_message": "MT564 / MT566 / seev.031 generated",
                "swift_mt564": swift_mt564,
                "swift_mt566": swift_mt566,
                "iso20022_seev031": iso20022_seev,
                "swift_validation": mt564_val,
                "processed_at": datetime.utcnow().isoformat(),
            },
            executed_at=datetime.utcnow().isoformat(),
        )
