import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.config import AZURE_COSMOS_ENDPOINT, AZURE_COSMOS_KEY, COSMOS_DATABASE

logger = logging.getLogger("mailmind.cosmos")


class CosmosService:
    """
    Azure Cosmos DB Persistence & Compliance Audit Trail Service.
    Stores:
      - Raw & sanitized email records
      - Multi-agent pipeline decisions & step telemetry
      - Actions executed and human approvals for full regulatory compliance
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

    def save_email(self, email_data: dict) -> bool:
        email_id = str(email_data.get("id", "unknown"))
        self._emails[email_id] = {**email_data, "saved_at": datetime.utcnow().isoformat()}

        if self.emails_container:
            try:
                # Cosmos requires 'id' property
                doc = {**email_data, "id": email_id, "emailId": email_id}
                self.emails_container.upsert_item(doc)
                return True
            except Exception as e:
                logger.warning("Cosmos DB upsert email error: %s", e)
        return True

    def save_audit_trail(self, audit_record: dict) -> bool:
        trace_id = str(audit_record.get("trace_id", "unknown"))
        self._audit_trails[trace_id] = audit_record

        if self.audit_container:
            try:
                doc = {**audit_record, "id": trace_id, "traceId": trace_id}
                self.audit_container.upsert_item(doc)
                return True
            except Exception as e:
                logger.warning("Cosmos DB upsert audit error: %s", e)
        return True

    def save_action(self, action_data: dict) -> bool:
        action_id = str(action_data.get("action_id", "unknown"))
        self._actions[action_id] = action_data

        if self.actions_container:
            try:
                doc = {**action_data, "id": action_id, "actionId": action_id}
                self.actions_container.upsert_item(doc)
                return True
            except Exception as e:
                logger.warning("Cosmos DB upsert action error: %s", e)
        return True

    def get_email(self, email_id: str) -> Optional[dict]:
        if self.emails_container:
            try:
                item = self.emails_container.read_item(item=email_id, partition_key=email_id)
                return item
            except Exception:
                pass
        return self._emails.get(email_id)

    def get_audit_trail(self, trace_id: str) -> Optional[dict]:
        if self.audit_container:
            try:
                item = self.audit_container.read_item(item=trace_id, partition_key=trace_id)
                return item
            except Exception:
                pass
        return self._audit_trails.get(trace_id)

    def list_recent_emails(self, limit: int = 50) -> list:
        if self.emails_container:
            try:
                query = f"SELECT TOP {limit} * FROM c ORDER BY c._ts DESC"
                items = list(self.emails_container.query_items(query=query, enable_cross_partition_query=True))
                if items:
                    return items
            except Exception as e:
                logger.warning("Cosmos query emails error: %s", e)
        return list(self._emails.values())[-limit:]

    def list_recent_actions(self, limit: int = 50) -> list:
        if self.actions_container:
            try:
                query = f"SELECT TOP {limit} * FROM c ORDER BY c._ts DESC"
                items = list(self.actions_container.query_items(query=query, enable_cross_partition_query=True))
                if items:
                    return items
            except Exception as e:
                logger.warning("Cosmos query actions error: %s", e)
        return list(self._actions.values())[-limit:]
