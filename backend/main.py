import json
import logging
import asyncio
from datetime import datetime
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.models.email_models import IncomingEmail
from backend.agents.orchestrator import MailMindOrchestrator
from backend.services.cosmos_service import CosmosService
from backend.services.swift_engine import SWIFTEngine

from backend.services.compliance_report_generator import ComplianceReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("mailmind")


# ── WebSocket connection manager ─────────────────────────────────────────────

class ConnectionManager:
    """Manages WebSocket connections for real-time dashboard updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected (%d total)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(self.active_connections))

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected dashboard clients."""
        data = json.dumps(message, default=str)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)


manager = ConnectionManager()


# ── App setup ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🧠 MailMind starting up...")
    yield
    logger.info("🧠 MailMind shutting down...")


app = FastAPI(
    title="MailMind API",
    description="Intelligent Financial Email Automation Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = MailMindOrchestrator()
cosmos = orchestrator.cosmos
compliance_generator = ComplianceReportGenerator()
swift_engine = SWIFTEngine()

# ── In-memory stores for demo (fallback when Cosmos DB isn't configured) ─────

_processed_emails: list = []
_audit_records: list = []
_actions: list = []
_pending_approvals: dict = {}


# ── WebSocket endpoint ───────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; we mainly push from server side
            data = await websocket.receive_text()
            # Client can send ping/pong or commands
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── API Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/process-email")
async def process_email(email: IncomingEmail):
    """Process a single email through the full AI agent pipeline."""
    logger.info("Processing email: %s (from: %s)", email.subject, email.sender)

    # Broadcast pipeline start
    await manager.broadcast({
        "type": "pipeline_start",
        "email_id": email.id,
        "subject": email.subject,
        "timestamp": datetime.utcnow().isoformat(),
    })

    result = orchestrator.process_email(email)
    result_dict = result.model_dump() if hasattr(result, 'model_dump') else result

    # Store in memory
    _processed_emails.append({**email.model_dump(), "pipeline_result": result_dict})

    # Broadcast pipeline completion
    await manager.broadcast({
        "type": "pipeline_complete",
        "email_id": email.id,
        "result": result_dict,
        "timestamp": datetime.utcnow().isoformat(),
    })

    logger.info(
        "✅ Email processed: intent=%s, risk=%.2f, approval_needed=%s",
        result_dict.get("risk_level", "?"),
        result_dict.get("risk_score", 0),
        result_dict.get("requires_approval", False),
    )
    return result_dict


@app.post("/api/webhook/email")
async def email_webhook(payload: dict):
    """Webhook endpoint for Microsoft Graph API email notifications."""
    # Graph API validation
    if "validationToken" in payload:
        return payload["validationToken"]

    logger.info("Received Graph API webhook notification")
    # In production: fetch email via Graph API, then process
    return {"status": "received", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/emails")
async def list_emails():
    """List all processed emails."""
    try:
        db_emails = cosmos.list_recent_emails()
        if db_emails:
            return db_emails
    except Exception:
        pass
    return _processed_emails[-50:]


@app.get("/api/emails/{email_id}")
async def get_email(email_id: str):
    """Get details of a specific processed email."""
    # Check in-memory first
    for email in _processed_emails:
        if email.get("id") == email_id:
            return email
    try:
        result = cosmos.get_email(email_id)
        if result:
            return result
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Email not found")


@app.get("/api/audit/{trace_id}")
async def get_audit(trace_id: str):
    """Get audit trail for a specific trace."""
    try:
        audit = cosmos.get_audit_trail(trace_id)
        if audit:
            return audit
    except Exception:
        pass
    for record in _audit_records:
        if record.get("trace_id") == trace_id:
            return record
    raise HTTPException(status_code=404, detail="Audit trail not found")


@app.get("/api/compliance/certificate/{email_id}")
async def get_compliance_certificate(email_id: str, format: str = Query("json")):
    """
    Generate formal Regulatory Compliance Audit Certificate conforming to:
      1. MiFID II RTS 25 UTC Clock Synchronization (microsecond precision).
      2. FINRA Rule 4511 & SEC 17a-4 WORM 6-year retention ledger.
      3. Zero-PII Anonymization cryptographic proof.
      4. Multi-agent execution DAG lineage trace.
      5. Supervisor cryptographic approval signature hash.
    
    Supports format='json' (default) or format='html' for printable PDF certificate.
    """
    email_data = None
    pipeline_result = None
    audit_record = None

    # 1. Search in memory
    for email in _processed_emails:
        if email.get("id") == email_id:
            email_data = email
            pipeline_result = email.get("pipeline_result")
            break

    # 2. Search in Cosmos DB
    if not email_data:
        try:
            email_data = cosmos.get_email(email_id)
        except Exception:
            pass

    # 3. Search in sample emails dataset
    if not email_data:
        try:
            with open("backend/data/sample_emails.json") as f:
                sample_emails = json.load(f)
                for se in sample_emails:
                    if se.get("id") == email_id:
                        email_data = se
                        break
        except Exception:
            pass

    # 4. Search audit record
    for record in _audit_records:
        if record.get("email_id") == email_id:
            audit_record = record
            if not pipeline_result:
                pipeline_result = record.get("pipeline_result")
            break

    cert_data = compliance_generator.generate_certificate_data(
        email_id=email_id,
        email_data=email_data,
        pipeline_result=pipeline_result,
        audit_record=audit_record,
    )

    if format.lower() == "html":
        html_content = compliance_generator.generate_certificate_html(cert_data)
        return HTMLResponse(content=html_content, status_code=200)

    return cert_data


@app.get("/api/actions")
async def list_actions():
    """List all executed actions."""
    try:
        db_actions = cosmos.list_recent_actions()
        if db_actions:
            return db_actions
    except Exception:
        pass
    return _actions[-50:]


@app.post("/api/approve/{trace_id}")
async def approve_action(trace_id: str):
    """Approve a pending action (HITL flow)."""
    logger.info("Action approved: %s", trace_id)
    await manager.broadcast({
        "type": "action_approved",
        "trace_id": trace_id,
        "approved_by": "human_operator",
        "timestamp": datetime.utcnow().isoformat(),
    })
    return {
        "status": "approved",
        "trace_id": trace_id,
        "approved_by": "human_operator",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/reject/{trace_id}")
async def reject_action(trace_id: str):
    """Reject a pending action (HITL flow)."""
    logger.info("Action rejected: %s", trace_id)
    await manager.broadcast({
        "type": "action_rejected",
        "trace_id": trace_id,
        "rejected_by": "human_operator",
        "timestamp": datetime.utcnow().isoformat(),
    })
    return {
        "status": "rejected",
        "trace_id": trace_id,
        "rejected_by": "human_operator",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MailMind",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "openai": "connected" if orchestrator.openai.client else "mock_mode",
            "websocket_clients": len(manager.active_connections),
        },
    }


@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics."""
    total = len(_processed_emails)
    auto_executed = sum(1 for e in _processed_emails if not e.get("pipeline_result", {}).get("requires_approval", False))
    pending = sum(1 for e in _processed_emails if e.get("pipeline_result", {}).get("requires_approval", False))
    avg_risk = 0.0
    if total > 0:
        avg_risk = sum(
            e.get("pipeline_result", {}).get("risk_score", 0)
            for e in _processed_emails
        ) / total

    return {
        "total_processed": total,
        "auto_executed": auto_executed,
        "pending_approvals": pending,
        "avg_risk_score": round(avg_risk, 3),
        "intents": _count_intents(),
    }


def _count_intents() -> dict:
    counts = {}
    for e in _processed_emails:
        steps = e.get("pipeline_result", {}).get("steps", [])
        for step in steps:
            if step.get("agent_name") == "Classifier":
                intent = step.get("output_data", {}).get("intent", "UNKNOWN")
                counts[intent] = counts.get(intent, 0) + 1
    return counts


@app.post("/api/demo/trigger")
async def trigger_demo():
    """Trigger demo by processing all sample emails through the pipeline."""
    logger.info("🚀 Demo triggered — processing sample emails...")
    try:
        with open("backend/data/sample_emails.json") as f:
            emails = json.load(f)

        results = []
        for i, email_data in enumerate(emails):
            email = IncomingEmail(**email_data)
            logger.info("  [%d/%d] Processing: %s", i + 1, len(emails), email.subject)

            # Broadcast each email being processed
            await manager.broadcast({
                "type": "demo_email_start",
                "index": i + 1,
                "total": len(emails),
                "email_id": email.id,
                "subject": email.subject,
            })

            result = orchestrator.process_email(email)
            result_dict = result.model_dump() if hasattr(result, 'model_dump') else result
            results.append(result_dict)
            _processed_emails.append({**email.model_dump(), "pipeline_result": result_dict})

            await manager.broadcast({
                "type": "demo_email_complete",
                "index": i + 1,
                "total": len(emails),
                "email_id": email.id,
                "result": result_dict,
            })

        await manager.broadcast({
            "type": "demo_complete",
            "total_processed": len(results),
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.info("✅ Demo complete — %d emails processed", len(results))
        return {"status": "processed", "count": len(results), "results": results}

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Sample emails file not found")
    except Exception as e:
        logger.error("Demo failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── SWIFT ISO 15022 & ISO 20022 Endpoints ────────────────────────────────────

@app.get("/api/swift/samples")
async def get_swift_samples():
    """Returns generated SWIFT MT and ISO 20022 MX messages for all 5 sample emails."""
    try:
        samples = swift_engine.generate_all_sample_messages()
        return {"samples": samples, "count": len(samples)}
    except Exception as e:
        logger.error("Failed to generate SWIFT samples: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/swift/preview")
async def preview_swift_message(email: IncomingEmail):
    """Generates SWIFT MT (ISO 15022) and ISO 20022 MX representations for an incoming email."""
    try:
        email_dict = email.model_dump()
        mt_result = swift_engine.email_to_swift_mt(email_dict)
        mx_result = swift_engine.email_to_iso20022(email_dict)
        return {
            "email_id": email.id,
            "swift_mt": mt_result,
            "iso20022_mx": mx_result,
        }
    except Exception as e:
        logger.error("Failed to generate SWIFT preview: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/swift/validate")
async def validate_swift(payload: dict):
    """Validates raw SWIFT MT text or ISO 20022 XML."""
    raw_message = payload.get("message", "")
    if not raw_message:
        raise HTTPException(status_code=400, detail="Missing 'message' in payload")

    if raw_message.strip().startswith("<?xml") or raw_message.strip().startswith("<Document"):
        # ISO 20022 XML Validation
        parsed = swift_engine.iso20022_to_entity(raw_message)
        is_valid = bool(parsed.get("root_tag"))
        return {
            "standard": "ISO 20022",
            "is_valid": is_valid,
            "parsed_entity": parsed,
            "errors": [] if is_valid else ["Invalid XML root or document structure"],
        }
    else:
        # ISO 15022 MT Validation
        report = swift_engine.validate_swift_message(raw_message)
        parsed_entity = swift_engine.swift_mt_to_entity(raw_message)
        return {
            "standard": "ISO 15022",
            "is_valid": report["is_valid"],
            "validation_report": report,
            "parsed_entity": parsed_entity,
        }

