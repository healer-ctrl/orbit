from typing import Dict, Any
import time
import uuid
from datetime import datetime, timedelta
from backend.models.action_models import ActionRequest, ActionResult, ActionStatus
from backend.services.swift_engine import SWIFTEngine


class SettlementHandler:
    """Simulates SSI correction and trade resubmission in a settlement system with SWIFT messaging."""

    def __init__(self):
        self.swift_engine = SWIFTEngine()

    def execute(self, request: ActionRequest) -> ActionResult:
        time.sleep(0.6)  # simulate settlement API latency

        instruction_id = f"INST-{uuid.uuid4().hex[:8].upper()}"
        payload = request.payload or {}
        trade_id = payload.get("trade_id", "TRD-998822")
        counterparty = payload.get("counterparty", "JPM")
        counterparty_bic = "CHASUS33XXX"
        amount = payload.get("amount", 2_450_000.00)
        currency = payload.get("currency", "USD")
        settlement_date = payload.get("settlement_date", (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"))

        # Generate SWIFT MT544 Settlement Confirmation / SSI Correction message
        swift_mt544 = self.swift_engine.generate_mt544(
            trade_id=trade_id,
            isin=payload.get("isin", "US0378331005"),
            instrument_name="T+1 Settlement Target2",
            amount=amount,
            currency=currency,
            settlement_date=settlement_date,
            counterparty_bic=counterparty_bic,
            safekeeping_account="COBADEFF",
            beneficiary_iban="DE44500105175407324931",
            narrative="SSI CORRECTION TARGET2 RESUBMISSION SUCCESS",
        )

        # Generate ISO 20022 pacs.008 credit transfer / settlement message
        iso20022_pacs008 = self.swift_engine.generate_pacs_008(
            transaction_id=trade_id,
            amount=amount,
            currency=currency,
            settlement_date=settlement_date,
            debtor_name="Société Générale Paris",
            creditor_name="JPMorgan Chase NY",
            remittance_info=f"SSI Correction TARGET2 Resubmission {trade_id}",
        )

        mt544_val = self.swift_engine.validate_swift_message(swift_mt544)

        return ActionResult(
            action_id=f"SET-{request.trace_id[:8]}",
            action_type=request.action_type,
            status=ActionStatus.SUCCESS,
            result_data={
                "instruction_id": instruction_id,
                "trade_id": trade_id,
                "counterparty": counterparty,
                "counterparty_bic": counterparty_bic,
                "settlement_system": "TARGET2",
                "original_ssi": {
                    "beneficiary_bic": "DEUTDEFF",
                    "account": "DE89370400440532013000",
                },
                "corrected_ssi": {
                    "beneficiary_bic": "COBADEFF",
                    "account": "DE44500105175407324931",
                },
                "settlement_date": settlement_date,
                "settlement_cycle": "T+1",
                "delivery_type": "DVP",
                "ssi_status": "CORRECTED",
                "resubmission_status": "RESUBMITTED",
                "matching_status": "PENDING_MATCH",
                "swift_message": "MT544 / pacs.008 resubmitted",
                "swift_mt544": swift_mt544,
                "iso20022_pacs008": iso20022_pacs008,
                "swift_validation": mt544_val,
                "deadline_met": True,
                "processed_at": datetime.utcnow().isoformat(),
            },
            executed_at=datetime.utcnow().isoformat(),
        )
