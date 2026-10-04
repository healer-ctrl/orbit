from typing import Dict, Any
import time
import uuid
from datetime import datetime
from backend.models.action_models import ActionRequest, ActionResult, ActionStatus
from backend.services.swift_engine import SWIFTEngine


class InstrumentCorrectionHandler:
    """Simulates patching reference data in an instrument master system with SWIFT CA notification."""

    def __init__(self):
        self.swift_engine = SWIFTEngine()

    def execute(self, request: ActionRequest) -> ActionResult:
        time.sleep(0.5)

        payload = request.payload or {}
        new_isin = payload.get("isin", "XS0987654323")
        instrument_name = payload.get("instrument_name", "Corporate Bond 5Y EUR")

        swift_mt564 = self.swift_engine.generate_mt564(
            corporate_action_ref=f"REORG-{request.trace_id[:8]}",
            isin=new_isin,
            instrument_name=instrument_name,
            event_type="EXWA",
            mandatory_flag="MAND",
            narrative="ISSUER REORGANIZATION ISIN UPDATE",
        )

        iso20022_seev = self.swift_engine.generate_seev_031(
            corporate_action_ref=f"REORG-{request.trace_id[:8]}",
            isin=new_isin,
            instrument_name=instrument_name,
            event_type="EXWA",
        )

        return ActionResult(
            action_id=f"IC-{request.trace_id[:8]}",
            action_type=request.action_type,
            status=ActionStatus.SUCCESS,
            result_data={
                "correction_id": f"COR-{uuid.uuid4().hex[:8].upper()}",
                "position_id": "POS-44332",
                "old_mapping": {
                    "isin": "XS1234567890",
                    "source": "AUTO_ENRICHMENT",
                    "last_updated": "2024-04-01T10:00:00Z",
                },
                "new_mapping": {
                    "isin": new_isin,
                    "source": "MAILMIND_CORRECTION",
                    "last_updated": datetime.utcnow().isoformat(),
                },
                "instrument_name": instrument_name,
                "instrument_type": "FIXED_INCOME",
                "affected_systems": [
                    "Reference Data Master",
                    "Position Keeper",
                    "Risk Engine",
                ],
                "downstream_notifications": 3,
                "validation": {
                    "isin_checksum": "VALID",
                    "bloomberg_cross_ref": "VERIFIED",
                },
                "swift_mt564": swift_mt564,
                "iso20022_seev031": iso20022_seev,
                "correction_status": "APPLIED",
                "rollback_available": True,
                "processed_at": datetime.utcnow().isoformat(),
            },
            executed_at=datetime.utcnow().isoformat(),
        )
