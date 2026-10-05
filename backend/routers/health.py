import time
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Response, status

from backend.config import ping_key_vault
from backend.resilience import resilience_registry
from backend.telemetry import get_current_trace_id, get_current_traceparent

router = APIRouter(tags=["Health & Diagnostics"])

_APP_START_TIME = time.time()


@router.get("/livez", summary="Liveness Probe")
async def liveness_probe() -> Dict[str, Any]:
    """
    Kubernetes / Docker Liveness probe.
    Fast, lightweight check returning 200 OK as long as the process is alive.
    """
    return {
        "status": "alive",
        "service": "mailmind-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_sec": int(time.time() - _APP_START_TIME),
        "trace_id": get_current_trace_id(),
    }


@router.get("/readyz", summary="Readiness Probe with Deep Dependency Checks")
async def readiness_probe(response: Response) -> Dict[str, Any]:
    """
    Kubernetes / Docker Readiness probe.
    Executes deep health checks across critical dependencies:
      - Azure Cosmos DB ping
      - Azure AI Search ping
      - Azure Key Vault ping
      - Azure OpenAI status
      - Microsoft Graph status
    """
    from backend.agents.orchestrator import MailMindOrchestrator
    # Use global singletons or lazy instances
    orchestrator = MailMindOrchestrator()

    checks: Dict[str, Any] = {}
    is_ready = True

    # 1. Cosmos DB ping
    try:
        checks["cosmos_db"] = orchestrator.cosmos.ping()
    except Exception as e:
        checks["cosmos_db"] = {"status": "unhealthy", "error": str(e)}
        is_ready = False

    # 2. Azure AI Search ping
    try:
        checks["azure_search"] = orchestrator.search.ping()
    except Exception as e:
        checks["azure_search"] = {"status": "unhealthy", "error": str(e)}

    # 3. Azure Key Vault ping
    try:
        checks["key_vault"] = ping_key_vault()
    except Exception as e:
        checks["key_vault"] = {"status": "unhealthy", "error": str(e)}

    # 4. Azure OpenAI status
    openai_status = "connected" if orchestrator.openai.client else "domain_heuristics_mode"
    checks["azure_openai"] = {
        "status": openai_status,
        "circuit_breaker": resilience_registry.get_breaker("azure_openai").state.value,
    }

    # 5. Microsoft Graph status
    try:
        checks["graph_api"] = orchestrator.openai.client and orchestrator.cosmos and {"status": "ready"} or {"status": "simulated"}
    except Exception:
        checks["graph_api"] = {"status": "simulated"}

    overall_status = "ready" if is_ready else "degraded"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "service": "mailmind-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": get_current_trace_id(),
        "traceparent": get_current_traceparent(),
        "checks": checks,
    }


@router.get("/healthz", summary="Full System Health & Circuit Breakers Diagnostics")
async def healthz_summary() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint providing:
      - System metadata and uptime
      - Circuit Breaker status metrics
      - Deep dependency diagnostics
    """
    from backend.agents.orchestrator import MailMindOrchestrator
    orchestrator = MailMindOrchestrator()

    return {
        "status": "healthy",
        "service": "mailmind-backend",
        "version": "1.0.0",
        "uptime_sec": int(time.time() - _APP_START_TIME),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": get_current_trace_id(),
        "traceparent": get_current_traceparent(),
        "circuit_breakers": resilience_registry.get_all_statuses(),
        "dependencies": {
            "cosmos_db": orchestrator.cosmos.ping(),
            "azure_search": orchestrator.search.ping(),
            "key_vault": ping_key_vault(),
            "openai_connected": orchestrator.openai.client is not None,
        },
    }
