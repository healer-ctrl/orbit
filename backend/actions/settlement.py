from typing import Dict, Any
import time
import uuid
from datetime import datetime, timedelta
from backend.models.action_models import ActionRequest, ActionResult, ActionStatus


class SettlementHandler:
    """Simulates SSI correction and trade resubmission in a settlement system."""

    def execute(self, request: ActionRequest) -> ActionResult:
        time.sleep(1.2)  # simulate longer settlement API latency

        instruction_id = f"INST-{uuid.uuid4().hex[:8].upper()}"
        payload = request.payload or {}

        return ActionResult(
            action_id=f"SET-{request.trace_id[:8]}",
            action_type=request.action_type,
            status=ActionStatus.SUCCESS,
            result_data={
                "instruction_id": instruction_id,
                "trade_id": payload.get("trade_id", "TRD-998822"),
                "counterparty": payload.get("counterparty", "JPM"),
                "counterparty_bic": "CHASUS33XXX",
                "settlement_system": "TARGET2",
                "original_ssi": {
                    "beneficiary_bic": "DEUTDEFF",
                    "account": "DE89370400440532013000",
                },
                "corrected_ssi": {
                    "beneficiary_bic": "COBADEFF",
                    "account": "DE44500105175407324931",
                },
                "settlement_date": payload.get("settlement_date", (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")),
                "settlement_cycle": "T+1",
                "delivery_type": "DVP",
                "ssi_status": "CORRECTED",
                "resubmission_status": "RESUBMITTED",
                "matching_status": "PENDING_MATCH",
                "swift_message": "MT544 resubmitted",
                "deadline_met": True,
                "processed_at": datetime.utcnow().isoformat(),
            },
            executed_at=datetime.utcnow().isoformat(),
        )
