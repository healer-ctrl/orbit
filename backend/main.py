import json
import logging
import time
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.models.email_models import IncomingEmail
from backend.agents.orchestrator import MailMindOrchestrator
from backend.telemetry import setup_logging, TraceContextMiddleware, init_tracer, get_current_trace_id, get_current_traceparent
from backend.routers.health import router as health_router
from backend.routers.observability import router as observability_router
from backend.routers.capital_markets import router as capital_markets_router
from backend.resilience import resilience_registry

# Initialize enterprise structured JSON logging and OpenTelemetry tracing
setup_logging(level="INFO", service_name="mailmind-backend")
init_tracer(service_name="mailmind-backend", service_version="1.0.0")

logger = logging.getLogger("mailmind")


# ── Custom Exceptions ────────────────────────────────────────────────────────

class ServiceUnavailableException(HTTPException):
    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int = 60, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": "60"},
        )


# ── Sliding Window Rate Limiter Middleware ───────────────────────────────────

class RateLimiter:
    """Sliding-window in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 120):
        self.requests_per_minute = requests_per_minute
        self.client_requests = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - 60
        self.client_requests[client_ip] = [
            ts for ts in self.client_requests[client_ip] if ts > window_start
        ]
        if len(self.client_requests[client_ip]) < self.requests_per_minute:
            self.client_requests[client_ip].append(now)
            return True
        return False

    def reset(self):
        self.client_requests.clear()
        self.requests_per_minute = 120


rate_limiter = RateLimiter(requests_per_minute=120)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Health probes and Swagger/OpenAPI docs are exempt from rate limiting
        exempt_paths = [
            "/healthz", "/livez", "/readyz",
            "/api/health", "/api/health/liveness", "/api/health/readiness",
            "/docs", "/redoc", "/openapi.json", "/ws",
        ]
        if any(request.url.path.startswith(p) for p in exempt_paths):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": "60", "X-RateLimit-Limit": str(rate_limiter.requests_per_minute)},
                content={
                    "error": "Too Many Requests",
                    "status_code": 429,
                    "detail": "Rate limit exceeded. Please retry in 60 seconds.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "trace_id": get_current_trace_id(),
                },
            )

        return await call_next(request)


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
        if websocket in self.active_connections:
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
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()


# ── App setup ────────────────────────────────────────────────────────────────

orchestrator = MailMindOrchestrator()
cosmos = orchestrator.cosmos


async def auto_poll_mailbox_worker():
    """Continuous automated background worker that syncs unread emails from orbit25690@outlook.com via Graph API."""
    logger.info("📬 [Auto-Sync Daemon] Started for orbit25690@outlook.com (continuous 30s background loop)")
    seen_ids = set()
    while True:
        try:
            messages = orchestrator.graph.fetch_recent_inbox_messages(limit=10, mailbox_user="orbit25690@outlook.com")
            for msg in messages:
                msg_id = msg.get("id")
                if msg_id and msg_id not in seen_ids:
                    seen_ids.add(msg_id)
                    inc_email = IncomingEmail(
                        id=msg_id,
                        sender=msg.get("sender", "unknown"),
                        subject=msg.get("subject", "No Subject"),
                        body=msg.get("body", ""),
                        received_at=msg.get("received_at", datetime.now(timezone.utc).isoformat()),
                        attachments=[],
                        raw_headers={},
                    )
                    logger.info("⚡ [Auto-Ingest] Processing incoming email automatically: %s", inc_email.subject)
                    result = orchestrator.process_email(inc_email)
                    intent_str = result.intent.value if hasattr(result, "intent") and hasattr(result.intent, "value") else str(getattr(result, "intent", "PROCESSED"))
                    await manager.broadcast({
                        "type": "email_processed",
                        "email_id": msg_id,
                        "subject": inc_email.subject,
                        "intent": intent_str,
                        "status": getattr(result, "status", "AUTO_EXECUTED"),
                    })
        except Exception as e:
            logger.debug("Auto-poll background worker heartbeat: %s", e)
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🧠 MailMind Enterprise Backend starting up with OpenTelemetry & Circuit Breakers...")
    # Start continuous automated background inbox polling daemon
    poll_task = asyncio.create_task(auto_poll_mailbox_worker())
    yield
    poll_task.cancel()
    logger.info("🧠 MailMind Enterprise Backend shutting down cleanly...")


OPENAPI_TAGS = [
    {"name": "1. Trade Linkage", "description": "Block trade-to-Galaxy ID allocation and TARGET2 settlement verification."},
    {"name": "2. ELIOT System Failures", "description": "ELIOT front-to-back trading system matching breaks, exception remediation, and engine resubmission."},
    {"name": "3. Cash Flow (CF) Issues", "description": "Nostro/Vostro dividend entitlement break reconciliation and automated ledger adjustment."},
    {"name": "4. Instrument Creation", "description": "Master reference data onboarding, ISIN ISO 6166 checksum validation, and CUSIP/SEDOL mapping."},
    {"name": "5. Warrants Creation", "description": "Structured warrant issuance, strike/barrier termsheet registration, and Greeks calculation."},
    {"name": "6. Price Queries", "description": "Real-time composite bid/ask market data quotes and multi-asset portfolio batch valuation."},
    {"name": "7. Refinancing Rates", "description": "Central bank and money market benchmark curve publishing (€STR, SOFR, EURIBOR)."},
    {"name": "8. KPIs & Metrics", "description": "Straight-Through Processing (STP) metrics, SLA compliance, and daily Ops transaction statistics."},
]

app = FastAPI(
    title="Orbit Capital Markets & SRE Operations API",
    description="""
# 🚀 Orbit — Intelligent Financial Action Layer & Email Automation Platform
### Société Générale Capital Markets · Standardized OpenAPI Action Suite

This Swagger UI exposes the **Production Action Layer** for back-office operations:
* **Automated Mode**: Executed autonomously by Multi-Agent AI and Azure Functions.
* **Manual / Dev Mode**: Directly testable via these standardized REST endpoints.

---
    """,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
)

# OpenTelemetry W3C Distributed Tracing Middleware
app.add_middleware(TraceContextMiddleware)
app.add_middleware(RateLimitMiddleware)

# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Production Health Probes & Action Routers
app.include_router(health_router)
app.include_router(observability_router)
app.include_router(capital_markets_router)


# ── Custom Error Handlers ───────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "status_code": 422,
            "detail": exc.errors(),
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": get_current_trace_id(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    status_error_map = {
        404: "Not Found",
        429: "Too Many Requests",
        503: "Service Unavailable",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
    }
    error_title = status_error_map.get(exc.status_code, "HTTP Error")
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": error_title,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": get_current_trace_id(),
        },
    )


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
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── API Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/process-email")
async def process_email(email: IncomingEmail, request: Request):
    """Process a single email through the full multi-agent pipeline with W3C trace propagation."""
    traceparent = getattr(request.state, "traceparent", None)
    logger.info("Processing email: %s (from: %s)", email.subject, email.sender)

    # Broadcast pipeline start
    await manager.broadcast({
        "type": "pipeline_start",
        "email_id": email.id,
        "subject": email.subject,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "traceparent": traceparent,
    })

    result = orchestrator.process_email(email, parent_traceparent=traceparent)
    result_dict = result.model_dump() if hasattr(result, 'model_dump') else result

    # Store in memory
    _processed_emails.append({**email.model_dump(), "pipeline_result": result_dict})

    # Broadcast pipeline completion
    await manager.broadcast({
        "type": "pipeline_complete",
        "email_id": email.id,
        "result": result_dict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(
        "✅ Email processed: intent=%s, risk=%.2f, approval_needed=%s, trace_id=%s",
        result_dict.get("risk_level", "?"),
        result_dict.get("risk_score", 0),
        result_dict.get("requires_approval", False),
        result_dict.get("trace_id", "none"),
    )
    return result_dict


@app.post("/api/webhook/email")
async def email_webhook(payload: dict):
    """Webhook endpoint for Microsoft Graph API email notifications."""
    if "validationToken" in payload:
        return payload["validationToken"]

    logger.info("Received Graph API webhook notification")
    return {"status": "received", "timestamp": datetime.now(timezone.utc).isoformat()}


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
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "status": "approved",
        "trace_id": trace_id,
        "approved_by": "human_operator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/reject/{trace_id}")
async def reject_action(trace_id: str):
    """Reject a pending action (HITL flow)."""
    logger.info("Action rejected: %s", trace_id)
    await manager.broadcast({
        "type": "action_rejected",
        "trace_id": trace_id,
        "rejected_by": "human_operator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "status": "rejected",
        "trace_id": trace_id,
        "rejected_by": "human_operator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint with DLQ count and circuit breaker statuses."""
    dlq_count = len(orchestrator.dlq.list_dlq_messages())
    return {
        "status": "healthy",
        "service": "MailMind",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "openai": "connected" if orchestrator.openai.client else "mock_mode",
            "websocket_clients": len(manager.active_connections),
            "circuit_breakers": resilience_registry.get_all_statuses(),
            "dlq_pending_count": dlq_count,
        },
    }


@app.get("/api/health/liveness")
async def health_liveness_alias():
    """Alias to /livez for compatibility."""
    return {"status": "alive", "service": "mailmind-backend", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/health/readiness")
async def health_readiness_alias(response: Response):
    """Alias to /readyz for compatibility."""
    return {
        "status": "ready",
        "service": "mailmind-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "cosmos_db": orchestrator.cosmos.ping(),
            "azure_search": orchestrator.search.ping(),
        },
    }


# ── DLQ & Quarantine Endpoints ───────────────────────────────────────────────

@app.get("/api/dlq")
async def list_dlq():
    """List all Dead Letter Queue messages."""
    return [m.model_dump() for m in orchestrator.dlq.list_dlq_messages()]


@app.post("/api/dlq/{dlq_id}/replay")
async def replay_dlq(dlq_id: str):
    """Replay a message from DLQ."""
    result = orchestrator.dlq.replay_dlq_message(dlq_id, orchestrator_callable=orchestrator.process_email)
    return result


@app.get("/api/quarantine")
async def list_quarantine():
    """List all quarantined poison emails."""
    return [q.model_dump() for q in orchestrator.dlq.list_quarantined()]


@app.post("/api/quarantine/{quarantine_id}/release")
async def release_quarantine(quarantine_id: str):
    """Release a quarantined payload after manual security review."""
    result = orchestrator.dlq.release_quarantined(quarantine_id)
    if not result:
        raise HTTPException(status_code=404, detail="Quarantine record not found")
    return result.model_dump()


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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("✅ Demo complete — %d emails processed", len(results))
        return {"status": "processed", "count": len(results), "results": results}

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Sample emails file not found")
    except Exception as e:
        logger.error("Demo failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
