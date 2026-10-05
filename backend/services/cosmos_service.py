import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.config import AZURE_COSMOS_ENDPOINT, AZURE_COSMOS_KEY, COSMOS_DATABASE
from backend.resilience import resilience_registry, retry_with_backoff, CircuitBreakerOpenException
from backend.telemetry import get_tracer

logger = logging.getLogger("mailmind.services.cosmos")


class CosmosService:
    """
    Azure Cosmos DB Persistence & Compliance Audit Trail Service.
    Equipped with OpenTelemetry distributed tracing and resilient Circuit Breaker protection.
    """

    def __init__(self):
        self.endpoint = AZURE_COSMOS_ENDPOINT
        self.key = AZURE_COSMOS_KEY
        self.db_name = COSMOS_DATABASE
        self.client = None
        self.db = None
        self.emails_container = None
        self.audit_container = None
        self.actions_container = None
        self.breaker = resilience_registry.get_breaker("cosmos_db")
        self.tracer = get_tracer()

        # In-memory storage cache / fallback
        self._emails: Dict[str, Any] = {}
        self._audit_trails: Dict[str, Any] = {}
        self._actions: Dict[str, Any] = {}

        if self.endpoint and self.key:
            try:
                from azure.cosmos import CosmosClient
                self.client = CosmosClient(self.endpoint, credential=self.key)
                self.db = self.client.get_database_client(self.db_name)
                self.emails_container = self.db.get_container_client("emails")
                self.audit_container = self.db.get_container_client("audittrail")
                self.actions_container = self.db.get_container_client("actions")
                logger.info("Connected to Azure Cosmos DB: %s (DB: %s)", self.endpoint, self.db_name)
            except Exception as e:
                logger.warning("Could not connect to live Cosmos DB (%s). Using local resilient cache.", e)

    def ping(self) -> Dict[str, Any]:
        """Deep health check probe for Cosmos DB connectivity."""
        start = time.time()
        if not (self.endpoint and self.client and self.db):
            return {
                "status": "local_resilient_store",
                "latency_ms": 0,
                "cached_emails": len(self._emails),
                "cached_audit_records": len(self._audit_trails),
            }

        if self.breaker.state.value == "OPEN":
            return {
                "status": "circuit_open",
                "latency_ms": int((time.time() - start) * 1000),
                "endpoint": self.endpoint,
                "details": "Cosmos DB circuit is OPEN",
            }

        try:
            # Read database properties as a lightweight health check ping
            self.breaker.call(lambda: self.db.read())
            latency = int((time.time() - start) * 1000)
            return {
                "status": "healthy",
                "latency_ms": latency,
                "database": self.db_name,
                "endpoint": self.endpoint,
            }
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return {
                "status": "degraded",
                "latency_ms": latency,
                "error": str(e),
                "fallback": "in_memory_cache_active",
            }

    def save_email(self, email_data: dict) -> bool:
        with self.tracer.start_as_current_span("cosmos.save_email") as span:
            email_id = str(email_data.get("id", "unknown"))
            span.set_attribute("cosmos.email_id", email_id)
            self._emails[email_id] = {**email_data, "saved_at": datetime.now(timezone.utc).isoformat()}

            if self.emails_container:
                try:
                    doc = {**email_data, "id": email_id, "emailId": email_id}
                    self.breaker.call(lambda: self.emails_container.upsert_item(doc))
                    return True
                except Exception as e:
                    logger.warning("Cosmos DB upsert email error (%s). Cached in local memory.", e)
            return True

    def save_audit_trail(self, audit_record: dict) -> bool:
        with self.tracer.start_as_current_span("cosmos.save_audit_trail") as span:
            trace_id = str(audit_record.get("trace_id", "unknown"))
            span.set_attribute("cosmos.trace_id", trace_id)
            self._audit_trails[trace_id] = audit_record

            if self.audit_container:
                try:
                    doc = {**audit_record, "id": trace_id, "traceId": trace_id}
                    self.breaker.call(lambda: self.audit_container.upsert_item(doc))
                    return True
                except Exception as e:
                    logger.warning("Cosmos DB upsert audit error (%s). Cached in local memory.", e)
            return True

    def save_action(self, action_data: dict) -> bool:
        with self.tracer.start_as_current_span("cosmos.save_action") as span:
            action_id = str(action_data.get("action_id", "unknown"))
            span.set_attribute("cosmos.action_id", action_id)
            self._actions[action_id] = action_data

            if self.actions_container:
                try:
                    doc = {**action_data, "id": action_id, "actionId": action_id}
                    self.breaker.call(lambda: self.actions_container.upsert_item(doc))
                    return True
                except Exception as e:
                    logger.warning("Cosmos DB upsert action error (%s). Cached in local memory.", e)
            return True

    def get_email(self, email_id: str) -> Optional[dict]:
        with self.tracer.start_as_current_span("cosmos.get_email") as span:
            span.set_attribute("cosmos.email_id", email_id)
            if self.emails_container:
                try:
                    return self.breaker.call(
                        lambda: self.emails_container.read_item(item=email_id, partition_key=email_id)
                    )
                except Exception:
                    pass
            return self._emails.get(email_id)

    def get_audit_trail(self, trace_id: str) -> Optional[dict]:
        with self.tracer.start_as_current_span("cosmos.get_audit_trail") as span:
            span.set_attribute("cosmos.trace_id", trace_id)
            if self.audit_container:
                try:
                    return self.breaker.call(
                        lambda: self.audit_container.read_item(item=trace_id, partition_key=trace_id)
                    )
                except Exception:
                    pass
            return self._audit_trails.get(trace_id)

    def list_recent_emails(self, limit: int = 50) -> list:
        with self.tracer.start_as_current_span("cosmos.list_recent_emails") as span:
            if self.emails_container:
                try:
                    query = f"SELECT TOP {limit} * FROM c ORDER BY c._ts DESC"
                    items = list(self.breaker.call(
                        lambda: self.emails_container.query_items(query=query, enable_cross_partition_query=True)
                    ))
                    if items:
                        return items
                except Exception as e:
                    logger.warning("Cosmos query emails error: %s", e)
            return list(self._emails.values())[-limit:]

    def list_recent_actions(self, limit: int = 50) -> list:
        with self.tracer.start_as_current_span("cosmos.list_recent_actions") as span:
            if self.actions_container:
                try:
                    query = f"SELECT TOP {limit} * FROM c ORDER BY c._ts DESC"
                    items = list(self.breaker.call(
                        lambda: self.actions_container.query_items(query=query, enable_cross_partition_query=True)
                    ))
                    if items:
                        return items
                except Exception as e:
                    logger.warning("Cosmos query actions error: %s", e)
            return list(self._actions.values())[-limit:]
