import logging
import uuid
import time
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("mailmind.dlq")


class ThreatLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QuarantineStatus(str, Enum):
    QUARANTINED = "QUARANTINED"
    RELEASED = "RELEASED"
    PURGED = "PURGED"


class DLQStatus(str, Enum):
    PENDING = "PENDING"
    REPLAYED = "REPLAYED"
    FAILED_PERMANENT = "FAILED_PERMANENT"
    RESOLVED = "RESOLVED"


class QuarantinedEmail(BaseModel):
    quarantine_id: str = Field(default_factory=lambda: f"QRN-{uuid.uuid4().hex[:8].upper()}")
    email_id: str
    quarantined_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    reason: str
    threat_level: ThreatLevel = ThreatLevel.HIGH
    details: List[str] = Field(default_factory=list)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    status: QuarantineStatus = QuarantineStatus.QUARANTINED
    released_at: Optional[str] = None
    released_by: Optional[str] = None


class DLQMessage(BaseModel):
    dlq_id: str = Field(default_factory=lambda: f"DLQ-{uuid.uuid4().hex[:8].upper()}")
    email_id: str
    failed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: DLQStatus = DLQStatus.PENDING
    last_retry_at: Optional[str] = None
    resolution_notes: Optional[str] = None


class DeadLetterQueueService:
    """
    Enterprise Dead Letter Queue (DLQ) & Poison Email Quarantine Service.
    Handles:
      - Dead-lettering of unparseable, malformed, or failing email messages
      - Isolation and quarantine of malicious payloads (prompt injection, exploits)
      - Replay mechanisms for DLQ remediation
      - Regulatory audit tracking for quarantined security events
    """

    def __init__(self, cosmos_service=None):
        self.cosmos = cosmos_service
        self._dlq_store: Dict[str, DLQMessage] = {}
        self._quarantine_store: Dict[str, QuarantinedEmail] = {}

    # ── Quarantine Operations ────────────────────────────────────────────────

    def quarantine_email(
        self,
        email_id: str,
        raw_payload: Dict[str, Any],
        reason: str,
        threat_level: ThreatLevel = ThreatLevel.HIGH,
        details: Optional[List[str]] = None,
    ) -> QuarantinedEmail:
        """Isolates a malicious or policy-violating payload into secure quarantine."""
        quarantined = QuarantinedEmail(
            email_id=email_id,
            reason=reason,
            threat_level=threat_level,
            details=details or [],
            raw_payload=raw_payload,
        )
        self._quarantine_store[quarantined.quarantine_id] = quarantined
        logger.warning(
            "🚨 [QUARANTINE] Email %s quarantined (ID: %s, Threat: %s, Reason: %s)",
            email_id,
            quarantined.quarantine_id,
            threat_level.value,
            reason,
        )
        if self.cosmos:
            try:
                self.cosmos.save_audit_trail({
                    "trace_id": quarantined.quarantine_id,
                    "email_id": email_id,
                    "event_type": "SECURITY_QUARANTINE",
                    "threat_level": threat_level.value,
                    "reason": reason,
                    "details": details,
                    "created_at": quarantined.quarantined_at,
                })
            except Exception as e:
                logger.warning("Failed to persist quarantine audit to Cosmos: %s", e)
        return quarantined

    def list_quarantined(self, status: Optional[QuarantineStatus] = None) -> List[QuarantinedEmail]:
        """List all quarantined emails, optionally filtered by status."""
        items = list(self._quarantine_store.values())
        if status:
            items = [item for item in items if item.status == status]
        return sorted(items, key=lambda x: x.quarantined_at, reverse=True)

    def get_quarantined(self, quarantine_id: str) -> Optional[QuarantinedEmail]:
        """Retrieve a specific quarantined email record."""
        return self._quarantine_store.get(quarantine_id)

    def release_quarantined(self, quarantine_id: str, released_by: str = "security_officer") -> Optional[QuarantinedEmail]:
        """Releases a quarantined item after manual security validation."""
        record = self._quarantine_store.get(quarantine_id)
        if not record:
            return None
        record.status = QuarantineStatus.RELEASED
        record.released_at = datetime.utcnow().isoformat()
        record.released_by = released_by
        logger.info("🔓 [QUARANTINE] Released %s by %s", quarantine_id, released_by)
        return record

    def purge_quarantined(self, quarantine_id: str) -> bool:
        """Permanently purges a quarantined poison payload."""
        if quarantine_id in self._quarantine_store:
            self._quarantine_store[quarantine_id].status = QuarantineStatus.PURGED
            logger.info("🗑️ [QUARANTINE] Purged %s", quarantine_id)
            return True
        return False

    # ── Dead Letter Queue (DLQ) Operations ───────────────────────────────────

    def enqueue_failed(
        self,
        email_id: str,
        payload: Dict[str, Any],
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        max_retries: int = 3,
    ) -> DLQMessage:
        """Enqueues a failed or unparseable email payload to the Dead Letter Queue."""
        dlq_msg = DLQMessage(
            email_id=email_id,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            payload=payload,
            max_retries=max_retries,
        )
        self._dlq_store[dlq_msg.dlq_id] = dlq_msg
        logger.error(
            "📥 [DLQ] Enqueued email %s (DLQ ID: %s, Error: %s - %s)",
            email_id,
            dlq_msg.dlq_id,
            error_type,
            error_message,
        )
        return dlq_msg

    def list_dlq_messages(self, status: Optional[DLQStatus] = None) -> List[DLQMessage]:
        """List all DLQ messages, optionally filtered by status."""
        items = list(self._dlq_store.values())
        if status:
            items = [item for item in items if item.status == status]
        return sorted(items, key=lambda x: x.failed_at, reverse=True)

    def get_dlq_message(self, dlq_id: str) -> Optional[DLQMessage]:
        """Retrieve a specific DLQ message."""
        return self._dlq_store.get(dlq_id)

    def replay_dlq_message(self, dlq_id: str, orchestrator_callable=None) -> Dict[str, Any]:
        """
        Attempts to replay and reprocess a message from the Dead Letter Queue.
        """
        msg = self._dlq_store.get(dlq_id)
        if not msg:
            return {"success": False, "error": f"DLQ message {dlq_id} not found"}

        if msg.retry_count >= msg.max_retries:
            msg.status = DLQStatus.FAILED_PERMANENT
            return {
                "success": False,
                "error": f"Maximum retry limit ({msg.max_retries}) exceeded for {dlq_id}",
                "status": msg.status.value,
            }

        msg.retry_count += 1
        msg.last_retry_at = datetime.utcnow().isoformat()

        if orchestrator_callable:
            try:
                from backend.models.email_models import IncomingEmail
                email_obj = IncomingEmail(**msg.payload)
                result = orchestrator_callable(email_obj)
                msg.status = DLQStatus.RESOLVED
                msg.resolution_notes = f"Successfully replayed on retry #{msg.retry_count}"
                logger.info("✅ [DLQ] Replay succeeded for %s", dlq_id)
                return {
                    "success": True,
                    "dlq_id": dlq_id,
                    "status": msg.status.value,
                    "result": result.model_dump() if hasattr(result, "model_dump") else result,
                }
            except Exception as e:
                msg.error_message = str(e)
                if msg.retry_count >= msg.max_retries:
                    msg.status = DLQStatus.FAILED_PERMANENT
                logger.error("❌ [DLQ] Replay failed for %s: %s", dlq_id, e)
                return {
                    "success": False,
                    "dlq_id": dlq_id,
                    "error": str(e),
                    "retry_count": msg.retry_count,
                    "status": msg.status.value,
                }

        msg.status = DLQStatus.REPLAYED
        return {"success": True, "dlq_id": dlq_id, "status": msg.status.value}


# Singleton instance
dlq_service = DeadLetterQueueService()
