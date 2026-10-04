from typing import Dict, Any
import time
import uuid
from datetime import datetime
from backend.models.action_models import ActionRequest, ActionResult, ActionStatus


class TicketCreatorHandler:
    """Simulates creating an ITSM/ServiceNow support ticket."""

    def execute(self, request: ActionRequest) -> ActionResult:
        time.sleep(0.5)

        payload = request.payload or {}
        ticket_id = f"INC-{uuid.uuid4().hex[:6].upper()}"

        return ActionResult(
            action_id=f"TKT-{request.trace_id[:8]}",
            action_type=request.action_type,
            status=ActionStatus.SUCCESS,
            result_data={
                "ticket_id": ticket_id,
                "ticket_type": "INCIDENT",
                "category": "Access Management",
                "subcategory": "Application Access",
                "priority": "P3 - Medium",
                "summary": payload.get("summary", "System access provisioning request"),
                "description": f"Auto-created by MailMind AI from email. "
                               f"Requestor needs: {payload.get('action_type', 'Trade Entry, Settlement Read-Only')} access.",
                "requester": payload.get("counterparty", "John Doe"),
                "assignment_group": "IT Operations - Access Management",
                "assigned_to": "auto_assignment_queue",
                "sla_target": "4 business hours",
                "portal_url": f"https://servicenow.internal.bank/nav_to.do?uri=incident.do?sys_id={ticket_id}",
                "approval_required": False,
                "ticket_status": "NEW",
                "processed_at": datetime.utcnow().isoformat(),
            },
            executed_at=datetime.utcnow().isoformat(),
        )
